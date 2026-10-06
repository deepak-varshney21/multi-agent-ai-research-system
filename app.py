import re
import streamlit as st

from agents import (
    build_reader_agent,
    build_search_agent,
    writer_chain,
    critic_chain,
)


# ============================================================
# PAGE SETUP
# ============================================================

st.set_page_config(
    page_title="Multi-Agent Research System",
    page_icon="🔬",
    layout="wide",
)


# ============================================================
# HELPERS
# ============================================================

def extract_score(feedback: str):
    """Pull the 'Score: X/10' value out of critic feedback, robust to Markdown formatting."""
    
    match = re.search(r"\*?\*?Score\*?\*?:\s*(\d+)", feedback, re.IGNORECASE)

    return int(match.group(1)) if match else None


def extract_urls(text: str):
    """Extract and clean unique HTTP/HTTPS URLs from text."""

    urls = re.findall(
        r"https?://[^\s\]\)\">]+",
        text
    )

    cleaned = [
        u.rstrip(".,;:)'\"]")
        for u in urls
    ]

    # Remove duplicates while preserving order
    return list(dict.fromkeys(cleaned))


def show_friendly_error(e: Exception):
    """Display user-friendly messages for known API limits and network errors."""

    error_message = str(e).lower()

    # Rate limit / Quota errors
    if (
        "free-models-per-day" in error_message
        or "openrouter_free_tier_daily" in error_message
        or "rate limit exceeded" in error_message
        or "error code: 429" in error_message
        or "rate_limit_exceeded" in error_message
        or "tpm" in error_message
        or "rpm" in error_message
        or ("groq" in error_message and "rate" in error_message)
    ):

        st.warning(
            "⏳ Today's AI usage limit or rate limit has been reached.\n\n"
            "Please try again in a few minutes."
        )

    # Provider overloaded / 503
    elif (
        "provider_overloaded" in error_message
        or "service temporarily overloaded" in error_message
        or "error code: 503" in error_message
        or "503" in error_message
    ):

        st.warning(
            "⚠️ The AI service is temporarily busy.\n\n"
            "Please try again in a few minutes."
        )

    else:

        st.error(
            "❌ Something went wrong while running the research."
        )


# ============================================================
# MAIN PIPELINE
# ============================================================

def run_pipeline(topic: str):

    """
    Research Pipeline:

    Search → Reader → Writer → Critic → Final Report

    No revision loop.
    """

    state = {}


    # ========================================================
    # STEP 1 - SEARCH AGENT
    # ========================================================

    with st.status(
        "🔎 Step 1 — Search agent is working...",
        expanded=True
    ) as s:

        search_agent = build_search_agent()

        result = search_agent.invoke(
            {
                "messages": [
                    (
                        "user",
                        f"""Research the following topic:

{topic}

Find recent, reliable and detailed information.

IMPORTANT:
Return the results as a list of sources.

For EVERY source, include:
1. Source name
2. Page/article title
3. Full direct URL (starting with https://)

Example:
Source: World Bank
Title: Global Economic Impact of War
URL: https://example.com/article

Do not hide URLs inside markdown links without writing out the full URL.
"""
                    )
                ]
            }
        )

        state["search_results"] = (
            result["messages"][-1].content
        )

        # Search across all message contents (including tool outputs) for raw URLs
        all_messages_str = "\n".join(
            str(m.content) for m in result["messages"]
        )

        state["urls"] = extract_urls(
            all_messages_str
        )

        st.write(
            f"Found **{len(state['urls'])}** URLs."
        )

        s.update(
            label="🔎 Step 1 — Search complete",
            state="complete",
            expanded=False
        )


    # ========================================================
    # STEP 2 - READER AGENT
    # ========================================================

    with st.status(
        "📖 Step 2 — Reader agent is scraping top resources...",
        expanded=True
    ) as s:

        reader_agent = build_reader_agent()

        # Use maximum 3 URLs
        top_urls = state["urls"][:3]

        if top_urls:

            for u in top_urls:
                st.write(f"• {u}")

            reader_result = reader_agent.invoke(
                {
                    "messages": [
                        (
                            "user",
                            f"""
Research topic: {topic}

Here are the URLs found by the search agent:

{chr(10).join(top_urls)}

Select the most relevant URL and scrape it for deeper content.

Extract:

- important facts
- statistics
- key findings
- evidence
- source details

Keep the response focused and concise.
"""
                        )
                    ]
                }
            )

            state["scraped_content"] = (
                reader_result["messages"][-1].content
            )

        else:

            # No URL found
            st.warning(
                "⚠️ No URLs were found by the Search Agent."
            )

            state["scraped_content"] = (
                "No additional web pages were available for scraping."
            )

        s.update(
            label="📖 Step 2 — Scraping complete",
            state="complete",
            expanded=False
        )


    # ========================================================
    # STEP 3 - WRITER
    # ========================================================

    with st.status(
        "✍️ Step 3 — Writer is drafting the report...",
        expanded=False
    ) as s:

        research_combined = (
            f"SEARCH RESULTS:\n"
            f"{state['search_results']}\n\n"
            f"DETAILED SCRAPED CONTENT:\n"
            f"{state['scraped_content']}"
        )

        state["report"] = writer_chain.invoke(
            {
                "topic": topic,
                "research": research_combined
            }
        )

        s.update(
            label="✍️ Step 3 — Draft ready",
            state="complete"
        )


    # ========================================================
    # STEP 4 - CRITIC
    # ========================================================

    with st.status(
        "🧐 Step 4 — Critic is reviewing the report...",
        expanded=False
    ) as s:

        state["feedback"] = critic_chain.invoke(
            {
                "report": state["report"]
            }
        )

        score = extract_score(
            state["feedback"]
        )

        state["score"] = score

        st.write(
            f"Score: **{score if score is not None else 'N/A'}/10**"
        )

        s.update(
            label=(
                f"🧐 Step 4 — Critic score: "
                f"{score if score is not None else 'N/A'}/10"
            ),
            state="complete"
        )


    # ========================================================
    # FINAL REPORT
    # ========================================================

    state["final_report"] = state["report"]

    return state


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("🧠 Research Assistant")

    st.markdown(
        """
        Your AI-powered multi-agent research system.

        The system automatically searches for information,
        reads sources, generates a report, and evaluates
        the final report using an AI critic.
        """
    )

    st.divider()

    st.subheader("🔄 Research Pipeline")

    st.markdown(
        """
        **1. 🔍 Search Agent**  
        Finds recent and reliable sources.

        **2. 📄 Reader Agent**  
        Reads and extracts important information.

        **3. ✍️ Writer Agent**  
        Generates a structured research report.

        **4. 🧐 Critic Agent**  
        Evaluates the final report quality.
        """
    )

    st.divider()

    st.subheader("✨ Features")

    st.markdown(
        """
        - 🌐 Web-based research
        - 🤖 Multiple AI agents
        - 📚 Source-based answers
        - 🧠 Automatic evaluation
        - 📥 Markdown report download
        """
    )

    st.divider()

    st.caption("Multi-Agent Research System")
    st.caption("Powered by AI 🤖")


# ============================================================
# MAIN UI
# ============================================================

st.title("🔬 Multi-Agent Research System")

st.caption(
    "Search → Read → Write → Critique, all automated."
)


topic = st.text_input(
    "Research topic",
    placeholder="e.g. Impact of quantum computing on cryptography",
)


run = st.button(
    "🚀 Run research",
    type="primary",
    disabled=not topic.strip()
)


# ============================================================
# RUN PIPELINE
# ============================================================

if run:

    st.session_state.pop(
        "result",
        None
    )

    try:

        st.session_state["result"] = run_pipeline(
            topic.strip()
        )

        st.session_state["topic"] = topic.strip()

    except Exception as e:

        show_friendly_error(e)

        with st.expander("🔍 Technical Error Details"):
            st.error(f"Error Type: {type(e).__name__}")
            st.code(str(e))


# ============================================================
# RESULTS
# ============================================================

result = st.session_state.get(
    "result"
)


if result:

    st.divider()


    # ========================================================
    # METRICS
    # ========================================================

    c1, c2 = st.columns(2)

    c1.metric(
        "Critic score",
        (
            f"{result['score']}/10"
            if result["score"] is not None
            else "N/A"
        )
    )

    c2.metric(
        "Sources found",
        len(result["urls"])
    )


    # ========================================================
    # TABS
    # ========================================================

    (
        tab_report,
        tab_feedback,
        tab_scraped,
        tab_search
    ) = st.tabs(
        [
            "📄 Final Report",
            "🧐 Critic Feedback",
            "📖 Scraped Content",
            "🔎 Search Results",
        ]
    )


    # ========================================================
    # FINAL REPORT TAB
    # ========================================================

    with tab_report:

        st.markdown(
            result["final_report"]
        )

        st.download_button(
            "⬇️ Download report (.md)",
            data=result["final_report"],
            file_name="research_report.md",
            mime="text/markdown",
        )


    # ========================================================
    # CRITIC TAB
    # ========================================================

    with tab_feedback:

        st.markdown(
            result["feedback"]
        )


    # ========================================================
    # SCRAPED CONTENT TAB
    # ========================================================

    with tab_scraped:

        st.markdown(
            result["scraped_content"]
        )


    # ========================================================
    # SEARCH RESULTS TAB
    # ========================================================

    with tab_search:

        st.markdown(
            result["search_results"]
        )

        if result["urls"]:

            st.write("**Extracted URLs**")

            for u in result["urls"]:

                st.markdown(
                    f"- {u}"
                )