"""
app.py
AI Marketing Co-Pilot - Streamlit MVP
Run with: streamlit run app.py
Requires env var GROQ_API_KEY to be set before launch.
"""

import os
import streamlit as st
from grok_client import call_grok, GrokAPIError
import pipeline
import prompts

st.set_page_config(page_title="AI Marketing Co-Pilot", page_icon="🚀", layout="wide")

if "context" not in st.session_state:
    st.session_state.context = None
if "business" not in st.session_state:
    st.session_state.business = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# ---------- HEADER ----------
st.title("🚀 AI Marketing Co-Pilot")
st.caption("Your AI-powered marketing strategist for startups and small businesses.")

# ---------- API KEY CHECK ----------
if not os.getenv("GROQ_API_KEY"):
    st.error("Grok API configuration is missing. Please configure the API key before running the analysis.")

# ---------- INPUT FORM ----------
with st.form("business_form"):
    st.subheader("Tell us about your business")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Business Name", placeholder="GlowSkin")
        product = st.text_input("Product/Service", placeholder="Organic skincare products")
        location = st.text_input("Location / Target Country", placeholder="Pakistan")
        budget = st.text_input("Marketing Budget", placeholder="$500/month")
    with col2:
        audience = st.text_input("Target Audience", placeholder="Women aged 18-35")
        stage = st.selectbox("Business Stage",
                              ["Idea stage", "Early-stage startup", "Growing business", "Established business"])
        known_competitors = st.text_input("Known Competitors (optional)",
                                           placeholder="Leave blank if you don't know your competitors")
    description = st.text_area("Business Description",
                                placeholder="Briefly describe what your business does and what makes it different.")

    submitted = st.form_submit_button("🚀 Analyze My Business", use_container_width=True)

if submitted:
    if not product or not audience or not location:
        st.warning("Please provide your product/service, target audience, and target location for a more useful analysis.")
    elif not os.getenv("GROQ_API_KEY"):
        st.error("Grok API configuration is missing. Please configure the API key before running the analysis.")
    else:
        business = {
            "name": name or "Unnamed business",
            "product": product,
            "description": description,
            "location": location,
            "audience": audience,
            "budget": budget,
            "stage": stage,
            "known_competitors": known_competitors,
        }
        st.session_state.business = business
        st.session_state.chat_history = []

        progress_bar = st.progress(0, text="Starting analysis...")

        def update_progress(label, step, total):
            progress_bar.progress(step / total, text=f"Step {step}/{total}: {label}...")

        try:
            st.session_state.context = pipeline.run_pipeline(business, progress_callback=update_progress)
            progress_bar.progress(1.0, text="Done!")
        except GrokAPIError as e:
            if e.code == "MISSING_KEY":
                st.error("Grok API configuration is missing. Please configure the API key before running the analysis.")
            else:
                st.error("We couldn't complete the analysis right now. Please try again.")
                with st.expander("Technical details (for debugging)"):
                    st.code(f"{e.code}: {e.detail}")
            st.session_state.context = None


# ---------- RESULTS DASHBOARD ----------
ctx = st.session_state.context
biz = st.session_state.business

if ctx and biz:
    st.divider()
    st.header(f"Marketing Strategy for {biz['name']}")

    # Section 1: Business & Target Audience
    with st.expander("🎯 Business & Target Audience", expanded=True):
        s1 = ctx.get("stage1", {})
        if "raw_text" in s1:
            st.write(s1["raw_text"])
        else:
            st.markdown(f"**Business type:** {s1.get('business_type', '-')}")
            st.markdown(f"**Product category:** {s1.get('product_category', '-')}")
            st.markdown(f"**Target customer:** {s1.get('target_customer', '-')}")
            st.markdown(f"**Value proposition:** {s1.get('value_proposition', '-')}")
            st.markdown("**Customer needs:**")
            for n in s1.get("customer_needs", []):
                st.markdown(f"- {n}")
            st.markdown("**Marketing challenges:**")
            for c in s1.get("marketing_challenges", []):
                st.markdown(f"- {c}")
            st.info(f"Positioning opportunity: {s1.get('positioning_opportunity', '-')}")

    # Section 2: Competitor Landscape
    with st.expander("🔎 Competitor Landscape", expanded=True):
        s2 = ctx.get("stage2", {})
        if "raw_text" in s2:
            st.write(s2["raw_text"])
        else:
            st.caption(s2.get("disclaimer", "AI-generated market intelligence, not verified real-time data."))
            for c in s2.get("competitors", []):
                st.markdown(f"**{c.get('name')}** ({c.get('category')}) - {c.get('why_relevant')}")

    # Section 3: Competitor Analysis
    with st.expander("📊 Competitor Analysis", expanded=True):
        s3 = ctx.get("stage3", {})
        if "raw_text" in s3:
            st.write(s3["raw_text"])
        else:
            rows = s3.get("competitor_table", [])
            if rows:
                st.dataframe(
                    [{
                        "Name": r.get("name"),
                        "Audience": r.get("target_audience"),
                        "Price positioning": r.get("price_positioning"),
                        "Brand positioning": r.get("brand_positioning"),
                        "Main channels": ", ".join(r.get("main_channels", [])),
                        "Threat": r.get("threat_level"),
                        "Our opportunity": r.get("our_opportunity"),
                    } for r in rows],
                    use_container_width=True,
                )
                for r in rows:
                    with st.container(border=True):
                        st.markdown(f"**{r.get('name')}** - USP: {r.get('usp')}")
                        st.markdown(f"Strengths: {', '.join(r.get('strengths', []))}")
                        st.markdown(f"Weaknesses: {', '.join(r.get('weaknesses', []))}")

    # Section 4: Market Opportunities
    with st.expander("💡 Market Opportunities", expanded=True):
        s4 = ctx.get("stage4", {})
        if "raw_text" in s4:
            st.write(s4["raw_text"])
        else:
            for g in s4.get("gaps", []):
                with st.container(border=True):
                    st.markdown(f"**Gap:** {g.get('gap')}")
                    st.markdown(f"**Why it's an opportunity:** {g.get('why_opportunity')}")
                    st.markdown(f"**Target segment:** {g.get('target_segment')}")
                    st.markdown(f"**Recommended response:** {g.get('recommended_response')}")

    # Section 5: Positioning
    with st.expander("🎯 Recommended Positioning", expanded=True):
        s5 = ctx.get("stage5", {})
        if "raw_text" in s5:
            st.write(s5["raw_text"])
        else:
            st.success(s5.get("suggested_brand_message", ""))
            st.markdown(f"**Target customer:** {s5.get('recommended_target_customer', '-')}")
            st.markdown(f"**Brand positioning:** {s5.get('brand_positioning', '-')}")
            st.markdown(f"**Value proposition:** {s5.get('value_proposition', '-')}")
            st.markdown(f"**USP:** {s5.get('usp', '-')}")
            st.markdown(f"**Key differentiator:** {s5.get('key_differentiator', '-')}")

    # Section 6 & 7: Marketing Strategy + Content/Campaign
    with st.expander("📈 Marketing Strategy & 📱 Content Ideas", expanded=True):
        s6 = ctx.get("stage6", {})
        if "raw_text" in s6:
            st.write(s6["raw_text"])
        else:
            st.markdown("**Recommended channels:**")
            for ch in s6.get("recommended_channels", []):
                st.markdown(f"- **{ch.get('channel')}**: {ch.get('why')}")
            st.markdown("**Content types to use:**")
            for c in s6.get("content_types", []):
                st.markdown(f"- {c}")
            campaign = s6.get("campaign", {})
            if campaign:
                st.markdown(f"**Campaign concept: {campaign.get('name')}**")
                st.caption(f"Goal: {campaign.get('goal')}")
                for step in campaign.get("outline", []):
                    st.markdown(f"- {step.get('day_or_step')}: {step.get('content')}")

    # Section 8: 30-Day Action Plan
    with st.expander("📅 30-Day Action Plan", expanded=True):
        s7 = ctx.get("stage7", {})
        if "raw_text" in s7:
            st.write(s7["raw_text"])
        else:
            for week in s7.get("weeks", []):
                st.markdown(f"**{week.get('week')}**")
                for t in week.get("tasks", []):
                    st.markdown(f"- {t}")

    # Section 9: Optional Assistant
    st.divider()
    st.subheader("🤖 Ask Your Marketing Assistant")
    st.caption("Ask follow-up questions using your business context above (e.g. 'Give me 10 Instagram Reel ideas').")

    for role, msg in st.session_state.chat_history:
        with st.chat_message(role):
            st.write(msg)

    user_q = st.chat_input("Ask a marketing question...")
    if user_q:
        st.session_state.chat_history.append(("user", user_q))
        with st.chat_message("user"):
            st.write(user_q)
        try:
            system = prompts.assistant_system_prompt(biz, ctx)
            answer = call_grok(system, user_q, temperature=0.7, max_tokens=1400)
        except GrokAPIError:
            answer = "We couldn't complete that request right now. Please try again."
        st.session_state.chat_history.append(("assistant", answer))
        with st.chat_message("assistant"):
            st.write(answer)
