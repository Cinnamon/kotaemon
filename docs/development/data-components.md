# Data & Data Structure Components

The data & data structure components include:

- The `Document` class.
- The document store.
- The vector store.

## Data Loader

- PdfLoader
- Layout-aware with table parsing PdfLoader

  - MathPixLoader: To use this loader, you need MathPix API key, refer to [mathpix docs](https://docs.mathpix.com/#introduction) for more information
  - OCRLoader: This loader uses lib-table and Flax pipeline to perform OCR and read table structure from PDF file (TODO: add more info about deployment of this module).
  - Output:

    - Document: text + metadata to identify whether it is table or not

      ```
      - "source": source file name
      - "type": "table" or "text"
      - "table_origin": original table in markdown format (to be feed to LLM or visualize using external tools)
      - "page_label": page number in the original PDF document
      ```

## Document Store

- InMemoryDocumentStore

## Vector Store

- ChromaVectorStore
- InMemoryVectorStore
