import os
import re
import subprocess

def parse_config(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.read().strip().split('\n')
    
    course_title = None
    topics = []
    for line in lines:
        if line.startswith("Course Title:"):
            course_title = line.replace("Course Title:", "").strip()
        elif line.strip() and not line.startswith("Course Title:"):
            # Lines after "Topics:" are the slide topics
            if not line.lower().startswith("topics:"):
                # Try to extract topic text after numbering
                # e.g. "1. Overview of Deep Learning"
                match = re.match(r'\d+\.\s*(.*)', line.strip())
                if match:
                    topics.append(match.group(1).strip())
                else:
                    # If there's a line not matching numbering, just take as is
                    topics.append(line.strip())
    return course_title, topics

def generate_slide_prompt(course_title, summary_stack, topic):
    return f"""
You are preparing a series of lecture slides for a course titled "{course_title}".

So far, these are the summaries of previous slides:
{summary_stack}

Now please create the next slide. The next slide should cover: "{topic}"

Please return only valid HTML that fits into the `{{SLIDE_CONTENT}}` section of the given template. Include a heading and some explanatory text using HTML elements like <h2>, <p>, <ul>, <li>, etc., as needed.
"""

def summarize_slide_prompt(slide_content):
    # A simple prompt to get a brief summary of the slide
    return f"""
Summarize the following slide content in one or two sentences:

{slide_content}
"""

def run_prompt_through_anthropic(input_text, output_file, temperature=0.7):
    # Write prompt to input.txt
    with open('input.txt', 'w', encoding='utf-8') as f:
        f.write(input_text.strip())
    # Call the anthropic processor
    cmd = ["python", "anthropic_file_processor.py", "-i", "input.txt", "-o", output_file, "-t", str(temperature)]
    subprocess.run(cmd, check=True)
    # Read the output
    with open(output_file, 'r', encoding='utf-8') as f:
        return f.read().strip()

def insert_into_template(course_title, slide_title, slide_content, footer_notes=""):
    with open("slide_template.html", 'r', encoding='utf-8') as f:
        template = f.read()
    filled = template.replace("{{COURSE_TITLE}}", course_title)
    filled = filled.replace("{{SLIDE_TITLE}}", slide_title)
    filled = filled.replace("{{SLIDE_CONTENT}}", slide_content)
    filled = filled.replace("{{FOOTER_NOTES}}", footer_notes)
    return filled

def main():
    course_title, topics = parse_config("course_config.txt")

    # Ensure summary_stack.txt exists
    if not os.path.exists("summary_stack.txt"):
        open("summary_stack.txt", 'w', encoding='utf-8').close()

    for i, topic in enumerate(topics, start=1):
        # Read summary stack
        with open("summary_stack.txt", 'r', encoding='utf-8') as f:
            summary_stack = f.read().strip()
        
        # Generate slide prompt
        prompt = generate_slide_prompt(course_title, summary_stack, topic)
        
        # Get slide content
        slide_content = run_prompt_through_anthropic(prompt, "slide_content.html")

        # Insert into template
        slide_html = insert_into_template(course_title, f"Slide {i}", slide_content, "")
        slide_filename = f"slide_{i:02d}.html"
        with open(slide_filename, 'w', encoding='utf-8') as f:
            f.write(slide_html)
        print(f"Created {slide_filename}")

        # Summarize this slide and append to summary_stack
        summary_prompt = summarize_slide_prompt(slide_content)
        slide_summary = run_prompt_through_anthropic(summary_prompt, "slide_summary.txt")
        # Append summary to summary_stack.txt
        with open("summary_stack.txt", 'a', encoding='utf-8') as f:
            f.write(f"{i}. {slide_summary}\n")

    # Optionally, combine all slides:
    # python combine_all_slides.py
    # Uncomment the line below if you have that script ready.
    # subprocess.run(["python", "combine_all_slides.py"], check=True)

if __name__ == "__main__":
    main()

