import os
import re
import subprocess
import sys
from pathlib import Path

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

If you need clarification about the topic, respond with exactly "TOPIC_CLARIFICATION_NEEDED" and nothing else.

Otherwise, please return only valid HTML that fits into the `{{SLIDE_CONTENT}}` section of the given template. Include a heading and some explanatory text using HTML elements like <h2>, <p>, <ul>, <li>, etc., as needed.
"""

def summarize_slide_prompt(slide_content):
    # A simple prompt to get a brief summary of the slide
    return f"""
Summarize the following slide content in one or two sentences:

{slide_content}

If you need clarification about the content, respond with exactly "CONTENT_CLARIFICATION_NEEDED" and nothing else.
"""

def run_prompt_through_anthropic(input_text, output_file, temperature=0.7, max_retries=3):
    for attempt in range(max_retries):
        # Write prompt to input.txt
        with open(output_file.parent / 'input.txt', 'w', encoding='utf-8') as f:
            f.write(input_text.strip())
        # Call the anthropic processor
        cmd = ["python", "anthropic_file_processor.py", 
               "-i", str(output_file.parent / 'input.txt'),
               "-o", str(output_file),
               "-t", str(temperature)]
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError:
            print(f"Warning: anthropic_file_processor.py failed (attempt {attempt + 1}/{max_retries})")
            if attempt == max_retries - 1:
                return None
            continue

        # Read the output
        with open(output_file, 'r', encoding='utf-8') as f:
            response = f.read().strip()
            if response in ["TOPIC_CLARIFICATION_NEEDED", "CONTENT_CLARIFICATION_NEEDED"]:
                print(f"Warning: Language model needs clarification (attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    return None
                continue
            return response
    return None

def insert_into_template(course_title, slide_title, slide_content, footer_notes=""):
    with open("slide_template.html", 'r', encoding='utf-8') as f:
        template = f.read()
    filled = template.replace("{{COURSE_TITLE}}", course_title)
    filled = filled.replace("{{SLIDE_TITLE}}", slide_title)
    filled = filled.replace("{{SLIDE_CONTENT}}", slide_content)
    filled = filled.replace("{{FOOTER_NOTES}}", footer_notes)
    return filled

def main():
    # Add argument parsing for output directory
    output_dir = None
    if len(sys.argv) > 1:
        output_dir = Path(sys.argv[1])
        
    course_title, topics = parse_config("course_config.txt")
    
    if output_dir is None:
        # Create shorter directory name from first few words of course title
        words = course_title.lower().split()[:3]  # Take first 3 words
        dir_name = '_'.join(words).replace(":", "").replace("-", "_")
        slides_dir = Path(dir_name)
    else:
        slides_dir = output_dir
        
    slides_dir.mkdir(exist_ok=True)

    # Ensure summary_stack.txt exists in the slides directory
    summary_stack_path = slides_dir / "summary_stack.txt"
    if not summary_stack_path.exists():
        summary_stack_path.touch()

    for i, topic in enumerate(topics, start=1):
        # Read summary stack
        with open(summary_stack_path, 'r', encoding='utf-8') as f:
            summary_stack = f.read().strip()
        
        # Generate slide prompt
        prompt = generate_slide_prompt(course_title, summary_stack, topic)
        
        # Get slide content
        slide_content = run_prompt_through_anthropic(prompt, slides_dir / "slide_content.html")
        if slide_content is None:
            print(f"Warning: Skipping slide {i} due to content generation failure")
            continue

        # Insert into template
        slide_html = insert_into_template(course_title, f"Slide {i}", slide_content, "")
        slide_filename = slides_dir / f"slide_{i:02d}.html"
        with open(slide_filename, 'w', encoding='utf-8') as f:
            f.write(slide_html)
        print(f"Created {slide_filename}")

        # Summarize this slide and append to summary_stack
        summary_prompt = summarize_slide_prompt(slide_content)
        slide_summary = run_prompt_through_anthropic(summary_prompt, slides_dir / "slide_summary.txt")
        if slide_summary is None:
            print(f"Warning: Failed to generate summary for slide {i}")
            continue
            
        # Append summary to summary_stack.txt
        with open(summary_stack_path, 'a', encoding='utf-8') as f:
            f.write(f"{i}. {slide_summary}\n")

    # Optionally, combine all slides:
    # python combine_all_slides.py
    # Uncomment the line below if you have that script ready.
    # subprocess.run(["python", "combine_all_slides.py"], check=True)

if __name__ == "__main__":
    main()
