"""
This module aims to project high-dimensional embeddings
into a lower-dimensional space for visualization.

Refs:
1. [RAGxplorer](https://github.com/gabrielchua/RAGxplorer)
2. [RAGVizExpander](https://github.com/KKenny0/RAGVizExpander)
"""
from typing import List, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objs as go
import umap
from ktem.embeddings.manager import embedding_models_manager as embeddings

from kotaemon.base import BaseComponent, Node
from kotaemon.embeddings import BaseEmbeddings

VISUALIZATION_SETTINGS = {
    "Original Query": {"color": "red", "opacity": 1, "symbol": "cross", "size": 15},
    "Retrieved": {"color": "green", "opacity": 1, "symbol": "circle", "size": 10},
    "Chunks": {"color": "blue", "opacity": 0.4, "symbol": "circle", "size": 10},
    "Sub-Questions": {"color": "purple", "opacity": 1, "symbol": "star", "size": 15},
}


class CreateCitationVizPipeline(BaseComponent):
    """Creating PlotData for visualizing query results"""

    embedding: BaseEmbeddings = Node(
        default_callback=lambda _: embeddings.get_default()
    )
    projector: umap.UMAP = None

    def _set_up_umap(self, embeddings: np.ndarray):
        umap_transform = umap.UMAP().fit(embeddings)
        return umap_transform

    def _project_embeddings(self, embeddings, umap_transform) -> np.ndarray:
        umap_embeddings = np.empty((len(embeddings), 2))
        for i, embedding in enumerate(embeddings):
            umap_embeddings[i] = umap_transform.transform([embedding])
        return umap_embeddings

    def _get_projections(self, embeddings, umap_transform):
        projections = self._project_embeddings(embeddings, umap_transform)
        x = projections[:, 0]
        y = projections[:, 1]
        return x, y

    def _prepare_projection_df(
        self,
        document_projections: Tuple[np.ndarray, np.ndarray],
        document_text: List[str],
        plot_size: int = 3,
    ) -> pd.DataFrame:
        """Prepares a DataFrame for visualization from projections and texts.

        Args:
            document_projections (Tuple[np.ndarray, np.ndarray]):
                Tuple of X and Y coordinates of document projections.
            document_text (List[str]): List of document texts.
        """
        df = pd.DataFrame({"x": document_projections[0], "y": document_projections[1]})
        df["document"] = document_text
        df["document_cleaned"] = df.document.str.wrap(50).apply(
            lambda x: x.replace("\n", "<br>")[:512] + "..."
        )
        df["size"] = plot_size
        df["category"] = "Retrieved"
        return df

    def _plot_embeddings(self, df: pd.DataFrame) -> go.Figure:
        """
        Creates a Plotly figure to visualize the embeddings.

        Args:
            df (pd.DataFrame): DataFrame containing the data to visualize.

        Returns:
            go.Figure: A Plotly figure object for visualization.
        """
        fig = go.Figure()

        for category in df["category"].unique():
            category_df = df[df["category"] == category]
            settings = VISUALIZATION_SETTINGS.get(
                category,
                {"color": "grey", "opacity": 1, "symbol": "circle", "size": 10},
            )
            fig.add_trace(
                go.Scatter(
                    x=category_df["x"],
                    y=category_df["y"],
                    mode="markers",
                    name=category,
                    marker=dict(
                        color=settings["color"],
                        opacity=settings["opacity"],
                        symbol=settings["symbol"],
                        size=settings["size"],
                        line_width=0,
                    ),
                    hoverinfo="text",
                    text=category_df["document_cleaned"],
                )
            )

        fig.update_layout(
            height=500,
            legend=dict(y=100, x=0.5, xanchor="center", yanchor="top", orientation="h"),
        )
        return fig

    def run(self, context: List[str], question: str):
        embed_contexts = self.embedding(context)
        context_embeddings = np.array([d.embedding for d in embed_contexts])

        self.projector = self._set_up_umap(embeddings=context_embeddings)

        embed_query = self.embedding(question)
        query_projection = self._get_projections(
            embeddings=[embed_query[0].embedding], umap_transform=self.projector
        )
        viz_query_df = pd.DataFrame(
            {
                "x": [query_projection[0][0]],
                "y": [query_projection[1][0]],
                "document_cleaned": question,
                "category": "Original Query",
                "size": 5,
            }
        )

        context_projections = self._get_projections(
            embeddings=context_embeddings, umap_transform=self.projector
        )
        viz_base_df = self._prepare_projection_df(
            document_projections=context_projections, document_text=context
        )

        visualization_df = pd.concat([viz_base_df, viz_query_df], axis=0)
        fig = self._plot_embeddings(visualization_df)
        return fig
