"""Optional manual smoke test for the public search provider.

Run this file directly when network access is available. Keeping the search
under the main guard prevents pytest from making an internet request while
collecting the project's tests.
"""

if __name__ == "__main__":
    from ddgs import DDGS

    with DDGS() as search:
        results = search.text(
            "startup founder Canada software comapany",
            max_results=5,
        )

        for result in results:
            print(result["title"])
            print(result["href"])
            print(result["body"])
            print("-" * 40)
