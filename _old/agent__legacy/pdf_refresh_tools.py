import pdf_refresh_batch as pr

def pdf_refresh_run(root=None, limit=None, execute=True, dry_run=False):
    """Wrapper for pdf_refresh_batch.run_batch to work as a tool."""
    class Args:
        def __init__(self, r, l, e, d):
            self.root = r
            self.limit = l
            self.execute = e
            self.dry_run = d
    return pr.run_batch(Args(root, limit, execute, dry_run))

TOOLS = [
    {
        "name": "pdf_refresh",
        "desc": "Перепечатать PDF (batch)",
        "params": {"root": "путь к базе", "limit": "лимит"},
        "approval": True,
        "fn": pdf_refresh_run
    }
]
