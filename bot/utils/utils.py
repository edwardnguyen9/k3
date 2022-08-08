async def pager(entries, chunk: int):
    for x in range(0, len(entries), chunk):
        yield entries[x : x + chunk]

def check_if_all_null(*args):
    for i in args:
        if i is not None: return False
    return True
