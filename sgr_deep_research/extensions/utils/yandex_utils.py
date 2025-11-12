def extractCloudFolder(base_url):
    """
    Extracts the cloud folder from a base_url of form
    "gpt://<cloud_folder>/..." (returns <cloud_folder>).
    Returns None if not matched.
    """
    prefix = "gpt://"
    if base_url.startswith(prefix):
        after_prefix = base_url[len(prefix):]
        return after_prefix.split("/", 1)[0]
    return None
