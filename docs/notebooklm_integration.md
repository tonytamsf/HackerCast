# NotebookLM Integration Plan

## Overview

As NotebookLM does not currently have a public API, we will use a browser automation tool to programmatically interact with the web interface. This document outlines the proposed approach using the **Selenium** library in Python.

## Tech Stack

*   **Language:** Python
*   **Browser Automation:** Selenium
*   **Web Browser:** Headless Chrome

## Automation Workflow

The following steps will be automated to generate a podcast script from a given article text:

1.  **Launch Headless Browser:**
    *   A headless instance of Google Chrome will be launched using Selenium's WebDriver.
    *   This will prevent a visible browser window from opening on the server.

2.  **Navigate to NotebookLM:**
    *   The script will navigate to the NotebookLM website (https://notebooklm.google.com/).
    *   The script will need to handle logging into a Google account if a session is not already active. This is a significant challenge and may require storing session cookies or using application-specific passwords if available.

3.  **Create a New Notebook:**
    *   The script will programmatically click the "New Notebook" button to create a new notebook for each daily run.
    *   The notebook can be named with the current date for easy identification.

4.  **Upload Article Text as a Source:**
    *   The script will locate the "Add Source" button and select the option to add a text source.
    *   The scraped article text will be pasted into the text area.
    *   The script will then click the "Add" or "Save" button to add the text as a source.

5.  **Input Master Prompt:**
    *   The script will locate the chat input field.
    *   The pre-defined master prompt for generating the podcast script will be entered into the input field.
    *   The script will then simulate pressing the "Enter" key or clicking the "Send" button.

6.  **Extract Generated Script:**
    *   The script will wait for NotebookLM to generate the response.
    *   It will then locate the HTML element containing the generated script.
    *   The text content of this element will be extracted and returned.

## Challenges and Risks

*   **UI Changes:** The biggest risk with this approach is that any change to the NotebookLM website's UI could break the automation script. The script will rely on specific HTML element IDs, class names, or XPath expressions to locate elements. These may change without notice.
*   **Authentication:** Handling Google account authentication can be complex and may require storing sensitive credentials or tokens. This needs to be handled securely.
*   **Error Handling:** The script needs to be robust enough to handle various errors, such as network issues, slow page loads, and unexpected pop-ups or dialogs.
*   **CAPTCHAs:** If Google detects unusual activity, it may present a CAPTCHA, which would be difficult to solve automatically.

## Mitigation Strategies

*   **Regular Maintenance:** The script will need to be regularly tested and updated to keep up with any changes to the NotebookLM website.
*   **Configuration:** Element selectors should be stored in a configuration file to make them easy to update without changing the code.
*   **Alerting:** The system should have alerting in place to notify developers if the automation script fails.
*   **API Watch:** We should continuously monitor for the release of an official NotebookLM API and switch to it as soon as it becomes available.
