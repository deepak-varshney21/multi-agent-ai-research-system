from agents import (
    build_reader_agent,
    build_search_agent,
    writer_chain,
    critic_chain
)

import re


def run_research_pipeline(topic: str) -> dict:

    state = {}

    # ============================================================
    # STEP 1 - SEARCH AGENT
    # ============================================================

    print("\n" + "=" * 50)
    print("STEP 1 - Search agent is working ...")
    print("=" * 50)

    search_agent = build_search_agent()

    search_result = search_agent.invoke({
    "messages": [
        (
            "user",
            f"""
Research the following topic:

{topic}

Find recent, reliable and detailed information.

IMPORTANT:
Return the results as a list of sources.

For EVERY source, include:
1. Source name
2. Page/article title
3. Full direct URL

The URLs MUST be complete URLs starting with:
https://

Do not hide URLs inside markdown links.

Example:

Source: World Bank
Title: Global Economic Impact of War
URL: https://example.com/article

Topic:
{topic}
"""
        )
    ]
})

    state["search_results"] = search_result["messages"][-1].content

    print("\nSearch result:\n")
    print(state["search_results"])


    # ============================================================
    # STEP 2 - READER AGENT
    # ============================================================

    print("\n" + "=" * 50)
    print("STEP 2 - Reader agent is scraping top resources ...")
    print("=" * 50)

    reader_agent = build_reader_agent()

    # Extract URLs from search result
    urls = re.findall(
        r'https?://[^\s\]\)]+',
        state["search_results"]
    )

    # Remove extra punctuation
    urls = [url.rstrip(".,;:") for url in urls]

    print("\nURLs found:")

    for url in urls[:3]:
        print(url)

    # Send only top 3 URLs to reader
    reader_result = reader_agent.invoke({
        "messages": [
            (
                "user",
                f"""
Research topic: {topic}

Here are the URLs found by the search agent:

{chr(10).join(urls[:3])}

Select the most relevant URL and scrape it for deeper content.

Extract:
- important facts
- statistics
- key findings
- evidence
- source details
"""
            )
        ]
    })

    state["scraped_content"] = reader_result["messages"][-1].content

    print("\nScraped content:\n")
    print(state["scraped_content"])


    # ============================================================
    # STEP 3 - WRITER
    # ============================================================

    print("\n" + "=" * 50)
    print("STEP 3 - Writer is drafting the report ...")
    print("=" * 50)

    research_combined = (
        f"SEARCH RESULTS:\n"
        f"{state['search_results']}\n\n"
        f"DETAILED SCRAPED CONTENT:\n"
        f"{state['scraped_content']}"
    )

    state["report"] = writer_chain.invoke({
        "topic": topic,
        "research": research_combined
    })

    print("\nFinal Report:\n")
    print(state["report"])


    # ============================================================
    # STEP 4 - CRITIC
    # ============================================================

    print("\n" + "=" * 50)
    print("STEP 4 - Critic is reviewing the report ...")
    print("=" * 50)

    state["feedback"] = critic_chain.invoke({
        "report": state["report"]
    })

    print("\nCritic report:\n")
    print(state["feedback"])


    # ============================================================
    # FINAL REPORT
    # ============================================================

    state["final_report"] = state["report"]

    print("\n" + "=" * 50)
    print("FINAL REPORT")
    print("=" * 50)

    print(state["final_report"])

    return state


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    topic = input("\nEnter a research topic: ")

    run_research_pipeline(topic)