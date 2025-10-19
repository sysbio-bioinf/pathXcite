Please read this disclaimer considering the data we distribute together with our tool pathXcite.
---

## External Data

This folder contains supporting data used by the tool. Most of these files are derived from public domain resources such as NCBI Gene, NCBI Taxonomy, PubTator, and Enrichr. Below is a description of each subfolder and file.

### Folder and File Descriptions

* **custom_gmt_files/**
  User-provided gene set libraries in GMT format. These are not distributed with the tool by default and are added manually.

* **gmt_sets/**
  Contains predefined gene set libraries downloaded from public resources such as Enrichr. These are not bundled directly with the tool but can be retrieved by the user at runtime.

* **gene2organism_mapping/**

  * `gene_summary.db`: SQLite database mapping Entrez Gene IDs to official gene symbols and optionally listing the source (for example, RefSeq). Built from NCBI bulk download data.
  * `tax2name.json`: JSON mapping of NCBI taxonomy IDs to scientific names.

* **background_genes.txt**
  List of gene symbols occurring in the Enrichr-provided gene set libraries. Contains only gene symbols without additional metadata.

* **enrichr_library_names.txt**
  A text file listing the names of more than 240 Enrichr gene set libraries available for download.

* **gmt_files_info.json**
  JSON file mapping each Enrichr gene set library to the number of terms and the approximate GMT file size in kilobytes.

* **gmt_libraries.json**
  JSON file mapping each Enrichr library to the number of terms it contains.

* **pubtator_count.db**
  SQLite database mapping Entrez Gene IDs to the total number of annotations associated with each gene, derived from PubTator data up to 2024.
  This will be regularly updated with new versions.

* **pubtator_doc_count.db**
  SQLite database mapping Entrez Gene IDs to the number of PubTator-annotated documents in which each gene appears.

### Data Sources

All gene identifiers, taxonomy information, and annotation counts are derived from publicly available data provided by NCBI Gene, NCBI Taxonomy, and PubTator. Gene set library names and metadata are derived from Enrichr. The tool does not redistribute the original GMT files from Enrichr; users may download them directly from the source.
