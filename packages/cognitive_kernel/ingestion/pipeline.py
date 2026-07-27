from .parser import PARSER_REGISTRY

def run_ingestion_pipeline(file_path: str, file_content: bytes):
    file_extension = "." + file_path.split(".")[-1]
    parser = PARSER_REGISTRY.get_parser(file_extension)

    if not parser:
        raise ValueError(f"No parser found for file type {file_extension}")

    parsed_data = parser.parse(file_content)
    # In a real implementation, we would then call the other methods
    # of the parser and do something with the extracted data.
    
    return {
        "metadata": parser.extract_metadata(parsed_data),
        "entities": parser.extract_entities(parsed_data),
    }
