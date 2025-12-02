import inspect
from langchain_postgres import PGVectorStore

print("PGVectorStore dir:")
print([m for m in dir(PGVectorStore) if not m.startswith("__")])

print("\ncreate_sync signature:")
print(inspect.signature(PGVectorStore.create_sync))

print("\nDocstring (truncated):")
doc = inspect.getdoc(PGVectorStore) or ""
print(doc.splitlines()[0:20])
