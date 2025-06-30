from openai import AzureOpenAI
import os

from app import logger

def generate_text(model: str, messages: list):
    
    try:
        client_4o = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY_4O"),
            api_version="2025-01-01-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT_4O")
        )
        logger.info("Connected to 4o-mini model")
    except Exception as e:
        error = "Unable to connect to OpenAI client: " + e
        logger.error(error + ": " + e)
        return error, e

    try:
        response = client_4o.chat.completions.create(
            model=model,
            messages=messages
        )
        generated_text = response.choices[0].message.content
        logger.info(f"Text generated")

        return generated_text, None
    
    except Exception as e:
        error = "Unable to generate text: " + e
        logger.error(error + ": " + e)
        return error, e
    
def process_summary(summary: str) -> str:

    # check the LLM formatted the output as bullet points
    if "•" not in summary:
        return summary
    
    # get each bullet point
    points = [i.strip() for i in summary.split("•") if len(i) > 2]#
    # start html bullet points
    combined_str = "<ul style='padding-left: 20px;'>"
    # iterate through each point, creating bullet point in html
    for item in points:
        combined_str += f"<li style='margin-bottom:5px;'>{item}</li>"
    # end html
    combined_str += "</ul>"

    return combined_str