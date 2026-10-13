import skills_index as S
v = S.embed("nomic-embed-text-v2-moe:latest", ["search_document: тест эмбеддинга для индекса скиллов дома"])
print("embed OK, dim:", len(v[0]) if v else 0)
