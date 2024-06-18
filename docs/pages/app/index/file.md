The file index stores files in a local folder and index them for retrieval.
This file index provides the following infrastructure to support the indexing:

- SQL table Source: store the list of files that are indexed by the system
- Vector store: contain the embedding of segments of the files
- Document store: contain the text of segments of the files. Each text stored
  in this document store is associated with a vector in the vector store.
- SQL table Index: store the relationship between (1) the source and the
  docstore, and (2) the source and the vector store.

The indexing and retrieval pipelines are encouraged to use the above software
infrastructure.

## Indexing pipeline

The ktem has default indexing pipeline: `ktem.index.file.pipelines.IndexDocumentPipeline`.

This default pipeline works as follow:

- **Input**: list of file paths
- **Output**: list of nodes that are indexed into database
- **Process**:
  - Read files into texts. Different file types has different ways to read texts.
  - Split text files into smaller segments
  - Run each segments into embeddings.
  - Store the embeddings into vector store. Store the texts of each segment
    into docstore. Store the list of files in Source. Store the linking
    between Sources and docstore + vectorstore in Index table.

You can customize this default pipeline if your indexing process is close to the
default pipeline. You can create your own indexing pipeline if there are too
much different logic.

### Customize the default pipeline

The default pipeline provides the contact points in `flowsettings.py`.

1. `FILE_INDEX_PIPELINE_FILE_EXTRACTORS`. Supply overriding file extractor,
   based on file extension. Example: `{".pdf": "path.to.PDFReader", ".xlsx": "path.to.ExcelReader"}`
2. `FILE_INDEX_PIPELINE_SPLITTER_CHUNK_SIZE`. The expected number of characters
   of each text segment. Example: 1024.
3. `FILE_INDEX_PIPELINE_SPLITTER_CHUNK_OVERLAP`. The expected number of
   characters that consecutive text segments should overlap with each other.
   Example: 256.

### Create your own indexing pipeline

Your indexing pipeline will subclass `BaseFileIndexIndexing`.

You should define the following methods:

- `run(self, file_paths)`: run the indexing given the pipeline
- `get_pipeline(cls, user_settings, index_settings)`: return the
  fully-initialized pipeline, ready to be used by ktem.
  - `user_settings`: is a dictionary contains user settings (e.g. `{"pdf_mode": True, "num_retrieval": 5}`). You can declare these settings in the `get_user_settings` classmethod. ktem will collect these settings into the app Settings page, and will supply these user settings to your `get_pipeline` method.
  - `index_settings`: is a dictionary. Currently it's empty for File Index.
- `get_user_settings`: to declare user settings, return a dictionary.

By subclassing `BaseFileIndexIndexing`, You will have access to the following resources:

- `self._Source`: the source table
- `self._Index`: the index table
- `self._VS`: the vector store
- `self._DS`: the docstore

Once you have prepared your pipeline, register it in `flowsettings.py`: `FILE_INDEX_PIPELINE = "<python.path.to.your.pipeline>"`.

## Retrieval pipeline

The ktem has default retrieval pipeline:
`ktem.index.file.pipelines.DocumentRetrievalPipeline`. This pipeline works as
follow:

- Input: user text query & optionally a list of source file ids
- Output: the output segments that match the user text query
- Process:
  - If a list of source file ids is given, get the list of vector ids that
    associate with those file ids.
  - Embed the user text query.
  - Query the vector store. Provide a list of vector ids to limit query scope
    if the user restrict.
  - Return the matched text segments

### Create your own retrieval pipeline

Your retrieval pipeline will subclass `BaseFileIndexRetriever`. The retriever
has the same database, vectorstore and docstore accesses like the indexing
pipeline.

You should define the following methods:

- `run(self, query, file_ids)`: retrieve relevant documents relating to the
  query. If `file_ids` is given, you should restrict your search within these
  `file_ids`.
- `get_pipeline(cls, user_settings, index_settings, selected)`: return the
  fully-initialized pipeline, ready to be used by ktem.
  - `user_settings`: is a dictionary contains user settings (e.g. `{"pdf_mode": True, "num_retrieval": 5}`). You can declare these settings in the `get_user_settings` classmethod. ktem will collect these settings into the app Settings page, and will supply these user settings to your `get_pipeline` method.
    - `index_settings`: is a dictionary. Currently it's empty for File Index.
    - `selected`: a list of file ids selected by user. If user doesn't select
      anything, this variable will be None.
- `get_user_settings`: to declare user settings, return a dictionary.

Once you build the retrieval pipeline class, you can register it in
`flowsettings.py`: `FILE_INDEXING_RETRIEVER_PIPELIENS = ["path.to.retrieval.pipelie"]`. Because there can be
multiple parallel pipelines within an index, this variable takes a list of
string rather than a string.

## Software infrastructure

| Infra            | Access        | Schema                                                                                                                                                                                                                                                                                      | Ref                                                        |
| ---------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| SQL table Source | self.\_Source | - id (int): id of the source (auto)<br>- name (str): the name of the file<br>- path (str): the path of the file<br>- size (int): the file size in bytes<br>- note (dict): allow extra optional information about the file<br>- date_created (datetime): the time the file is created (auto) | This is SQLALchemy ORM class. Can consult                  |
| SQL table Index  | self.\_Index  | - id (int): id of the index entry (auto)<br>- source_id (int): the id of a file in the Source table<br>- target_id: the id of the segment in docstore or vector store<br>- relation_type (str): if the link is "document" or "vector"                                                       | This is SQLAlchemy ORM class                               |
| Vector store     | self.\_VS     | - self.\_VS.add: add the list of embeddings to the vector store (optionally associate metadata and ids)<br>- self.\_VS.delete: delete vector entries based on ids<br>- self.\_VS.query: get embeddings based on embeddings.                                                                 | kotaemon > storages > vectorstores > BaseVectorStore       |
| Doc store        | self.\_DS     | - self.\_DS.add: add the segments to document stores<br>- self.\_DS.get: get the segments based on id<br>- self.\_DS.get_all: get all segments<br>- self.\_DS.delete: delete segments based on id                                                                                           | kotaemon > storages > docstores > base > BaseDocumentStore |
