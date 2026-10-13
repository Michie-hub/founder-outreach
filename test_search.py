from ddgs import DDGS

with DDGS() as search:
    results = search.text(
        "startup founder Canada software comapany",
        max_results=5
    )
    
    for result in results:
        print(result["title"])
        print(result["href"])
        print(result["body"])
        print("-" * 40)