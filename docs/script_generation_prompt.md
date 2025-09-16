# Script Generation Prompt for NotebookLM

## Overview

This document outlines the master prompt to be used with NotebookLM for generating a conversational podcast script from a given article. The prompt is designed to be standardized and well-engineered to produce consistent and high-quality output.

## The Master Prompt

```
You are a podcast host for "HackerCast: The Top 20 Daily". Your task is to create a short, engaging podcast script based on the provided article. The script should be conversational and easy to understand for a general tech audience.

**Article Title:** {{ARTICLE_TITLE}}

**Article Content:**
{{ARTICLE_CONTENT}}

**Instructions:**

1.  **Introduction:**
    *   Start with a friendly and engaging introduction.
    *   Mention the title of the article in a natural way.
    *   Briefly state the main topic of the article.

2.  **Summary:**
    *   Summarize the key points and main arguments of the article.
    *   Use clear and simple language. Avoid jargon where possible, or explain it briefly if necessary.
    *   The summary should be the main body of the script.

3.  **Conclusion:**
    *   Provide a concluding sentence that wraps up the discussion.
    *   You can end with a thought-provoking question or a final takeaway message.

4.  **Tone and Style:**
    *   The tone should be enthusiastic, curious, and informative.
    *   The script should be written as if it were being spoken, not read.
    *   Use contractions (e.g., "it's", "don't") to make it sound more natural.

5.  **Length:**
    *   The total length of the script should be between 300 and 500 words, which should correspond to an audio duration of approximately 3-5 minutes.

**Output Format:**

Please provide the script as clean text, without any additional formatting or commentary. The script should be ready to be sent directly to a text-to-speech (TTS) engine.

**Example Structure:**

(Intro)
Hey everyone, and welcome back to HackerCast! Today, we're diving into an interesting article titled "{{ARTICLE_TITLE}}". It talks about...

(Summary)
So, the main idea here is that...
The author also makes a great point about...
And finally, they discuss how...

(Conclusion)
All in all, this is a fascinating read that really makes you think about... What are your thoughts on this? Let us know!

---

Now, generate the podcast script based on the provided article content.
```

## Prompt Refinement

The quality of the generated script will depend heavily on the quality of the prompt. The following are some ideas for refining the prompt based on the output from NotebookLM:

*   **Adjusting the length:** If the scripts are consistently too long or too short, the word count in the prompt can be adjusted.
*   **Improving the tone:** If the tone is not quite right, more specific instructions can be added to the "Tone and Style" section.
*   **Handling different article types:** The prompt may need to be adjusted for different types of articles, such as tutorials, opinion pieces, or news reports.
*   **Adding more structure:** If the scripts lack structure, more specific instructions can be added to the "Example Structure" section.

By iterating on the prompt design, we can improve the quality of the generated scripts over time.
