# begin generate_slides.py
# This script generates HTML slides from a course outline using AI assistance.
# It works in the following way:

# SETUP AND CONFIGURATION
# ----------------------
# 1. Takes a course outline file (course_config.txt) as input
# 2. Can resume from previous runs by:
# - Finding highest numbered existing slide
# - Reading previous slide summaries for context
# - Continuing from where it left off
# 3. Supports test mode to only generate 5 slides for testing

# MAIN WORKFLOW
# ------------
# 1. Parses course config file to extract:
# - Course title
# - List of topics to cover
# 2. For each topic:
# - Generates a prompt for the AI using:
#   * Course title
#   * Previous slide summaries for context
#   * Current topic
# - Gets slide content from AI
# - Splits content into multiple slides if too long
# - Creates HTML slides using template
# - Generates summary of slide content
# - Maintains running summary stack for context

# KEY FEATURES
# -----------
# - Consistent slide formatting via HTML/CSS template
# - Maintains context between slides using summaries
# - Handles content overflow via slide splitting
# - Resumable from interruptions
# - Test mode for quick iterations
# - Strict limits on text per slide:
#   * Max 5 bullet points per slide
#   * Max 15 words per bullet point
#   * Max 2 levels of bullet nesting
#   * Min 24pt font size

import os
import re
import subprocess
import sys
import argparse
import json
from pathlib import Path
import glob

class CourseManager:
	def __init__(self, base_dir: Path):
		"""
		Initialize course manager with base directory for all courses

		Args:
			base_dir (Path): Base directory where all courses will be stored
		"""
		self.base_dir = Path(base_dir)
		self.courses_dir = self.base_dir / "courses"
		self.courses_dir.mkdir(parents=True, exist_ok=True)

	def create_course_directory(self, course_id: str) -> Path:
		"""
		Create directory structure for a new course

		Args:
			course_id (str): Unique identifier for the course

		Returns:
			Path: Path to the course directory
		"""
		course_dir = self.courses_dir / self._sanitize_id(course_id)
		course_dir.mkdir(parents=True, exist_ok=True)

		# Create subdirectories for course assets
		(course_dir / "slides").mkdir(exist_ok=True)
		(course_dir / "config").mkdir(exist_ok=True)
		(course_dir / "temp").mkdir(exist_ok=True)

		return course_dir

	def _sanitize_id(self, course_id: str) -> str:
		"""
		Sanitize course ID to be filesystem friendly

		Args:
			course_id (str): Raw course ID

		Returns:
			str: Sanitized course ID
		"""
		# Replace spaces and special characters with underscores
		sanitized = re.sub(r'[^\w\-]', '_', course_id)
		return sanitized.lower()

	def get_course_path(self, course_id: str) -> Path:
		"""
		Get path to course directory

		Args:
			course_id (str): Course identifier

		Returns:
			Path: Path to course directory
		"""
		return self.courses_dir / self._sanitize_id(course_id)

	def list_courses(self) -> list[dict]:
		"""
		List all courses in the base directory

		Returns:
			list[dict]: List of course information dictionaries
		"""
		courses = []
		for course_dir in self.courses_dir.iterdir():
			if course_dir.is_dir():
				config_file = course_dir / "config" / "course_config.txt"
				if config_file.exists():
					title, _ = parse_config(str(config_file))
					courses.append({
						"id": course_dir.name,
						"title": title,
						"path": str(course_dir),
						"slides_count": len(list((course_dir / "slides").glob("*.html")))
					})
		return courses

def parse_config(file_path):
	"""
	Parses course configuration file to extract title and topics.
	Handles multiple common formats for course outlines.
	"""
	with open(file_path, 'r', encoding='utf-8') as f:
		content = f.read().strip()

	# Extract course title - look for various formats
	title_patterns = [
		r"Course Title:\s*(.*?)(?:\n|$)",  # Standard format
		r"Title:\s*(.*?)(?:\n|$)",         # Shorter format
		r"^#\s*(.*?)(?:\n|$)",             # Markdown H1 format
		r"^=+\s*(.*?)\s*=+\s*$"            # Underlined format
	]

	course_title = None
	for pattern in title_patterns:
		match = re.search(pattern, content, re.MULTILINE)
		if match:
			course_title = match.group(1).strip()
			break

	if not course_title:
		# If no title found, use first non-empty line
		course_title = next((line.strip() for line in content.split('\n')
						   if line.strip()), "Untitled Course")

	# Extract topics using various patterns
	topics = []
	lines = content.split('\n')

	# Skip header section (everything before first blank line)
	content_start = 0
	for i, line in enumerate(lines):
		if not line.strip():
			content_start = i + 1
			break

	for line in lines[content_start:]:
		line = line.strip()
		if not line:
			continue

		# Skip common section headers
		if re.match(r'^(Part|Section|Module|Chapter)\s+\d+:', line, re.I):
			continue

		# Try various content patterns
		content = None
		patterns = [
			r'^\d+\.\s*(.*)',           # Numbered: "1. Topic"
			r'^[-*•]\s*(.*)',           # Bullet points
			r'^\([A-Z]\)\s*(.*)',       # Letter bullets: "(A) Topic"
			r'(?:Topic|Session):\s*(.*)',# Labeled lines
		]

		for pattern in patterns:
			match = re.match(pattern, line)
			if match:
				content = match.group(1).strip()
				break

		# If no pattern matched but line has content, include it
		if not content and line:
			# Skip common headers/labels
			if not re.match(r'^(Overview|Summary|Notes?|Objectives?):', line, re.I):
				content = line

		if content:
			topics.append(content)

	return course_title, topics

def generate_slide_prompt(course_title, summary_stack, topic):
	"""
	Creates prompt for AI to generate slide content.
	Includes context from previous slides via summary stack.
	"""
	return f"""
You are preparing a series of lecture slides for a course titled "{course_title}".

So far, these are the summaries of previous slides:
{summary_stack}

Now please create the next slide. The next slide should cover: "{topic}"

STRICT presentation requirements:
- Maximum 5 bullet points per slide
- Maximum 15 words per bullet point
- Maximum 2 levels of bullet point nesting
- Minimum font size of 24pt (use <style> tags)
- No paragraphs of text - only bullet points
- If content exceeds these limits, split into multiple slides with "<!--SPLIT_SLIDE_HERE-->"

If you need clarification about the topic, respond with exactly "TOPIC_CLARIFICATION_NEEDED" and nothing else.

Otherwise, please return only valid HTML that fits into the `{{SLIDE_CONTENT}}` section of the given template. Include a heading and bullet points using HTML elements like <h2>, <ul>, <li>, etc.

Even if you're not completely sure about some aspects of the topic, please provide your best attempt at creating concise slide content based on your current knowledge. Focus on the key concepts you're most confident about.
"""

def summarize_slide_prompt(slide_content):
	"""
	Creates prompt for AI to generate concise summary of slide content.
	Used to maintain context between slides.
	"""
	return f"""
Summarize the following slide content in one or two sentences:

{slide_content}

If you need clarification about the content, respond with exactly "CONTENT_CLARIFICATION_NEEDED" and nothing else.

Even if some aspects seem unclear, please provide your best attempt at a concise summary focusing on the main points you can confidently identify.
"""

def run_prompt_through_anthropic(input_text, output_file, temperature=0.7, max_retries=1):
	"""
	Sends prompt to Anthropic API model and handles response.
	Includes retry logic for failed attempts.
	"""
	output_dir = output_file.parent
	
	# Write prompt to input.txt in slides directory
	input_file = output_dir / 'input.txt'
	with open(input_file, 'w', encoding='utf-8') as f:
		f.write(input_text.strip())

	# Create stats file path in slides directory
	stats_file = output_dir / 'stats.json'
	
	# Call the anthropic processor
	cmd = ["python", "anthropic_file_processor.py",
		   "-i", str(input_file),
		   "-o", str(output_file),
		   "-t", str(temperature),
		   "--stats-file", str(stats_file)]

	for attempt in range(max_retries):
		try:
			result = subprocess.run(cmd, check=True, capture_output=True, text=True)

			# Read the output
			with open(output_file, 'r', encoding='utf-8') as f:
				response = f.read().strip()
				if response in ["TOPIC_CLARIFICATION_NEEDED", "CONTENT_CLARIFICATION_NEEDED"]:
					print(f"Warning: Language model needs clarification (attempt {attempt + 1}/{max_retries})")
					if attempt == max_retries - 1:
						print("Proceeding with best effort response...")
						return None
					continue
				return response

		except subprocess.CalledProcessError as e:
			print(f"Warning: anthropic_file_processor.py failed (attempt {attempt + 1}/{max_retries})")
			if e.stderr:
				print(f"Error output: {e.stderr}")
			if e.stdout:
				print(f"Output: {e.stdout}")
			if attempt == max_retries - 1:
				print("Proceeding with best effort response...")
				return None
			continue

	return None

def insert_into_template(course_title, slide_title, slide_content, footer_notes=""):
	"""
	Inserts generated content into HTML slide template.
	Template includes responsive design and consistent styling.
	"""
	template = """<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<title>{{SLIDE_TITLE}} - {{COURSE_TITLE}}</title>
	<style>
		:root {
			--main-font: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
		}
		body {
			font-family: var(--main-font);
			margin: 0;
			padding: 0;
			min-height: 100vh;
			display: flex;
			flex-direction: column;
		}
		main {
			flex: 1;
			padding: 2rem;
			max-width: 1200px;
			margin: 0 auto;
			width: 100%;
			box-sizing: border-box;
		}
		h1, h2 {
			color: #1a1a1a;
			line-height: 1.2;
		}
		h1 {
			font-size: 2.5rem;
			margin-bottom: 1.5rem;
		}
		h2 {
			font-size: 2rem;
			margin: 1rem 0;
		}
		p, li {
			font-size: 1.5rem;
			line-height: 1.5;
			color: #333;
		}
		ul {
			padding-left: 1rem;
			margin: 1rem 0;
			max-width: 1000px;
		}
		li {
			margin: 0.75rem 0;
			padding-left: 0.25rem;
		}
		/* Prevent deep nesting */
		li li li {
			display: none;
		}
		.header {
			background: #333;
			color: white;
			padding: 1rem 2rem;
			font-size: 1.25rem;
		}
		.footer {
			background: #f5f5f5;
			padding: 1rem 2rem;
			font-size: 1rem;
			border-top: 1px solid #ddd;
		}
		.slide-number {
			position: absolute;
			top: 1rem;
			right: 1rem;
			font-size: 1.25rem;
			color: #666;
		}
	</style>
</head>
<body>
	<div class="header">{{COURSE_TITLE}}</div>
	<main>
		{{SLIDE_CONTENT}}
	</main>
	<div class="footer">{{FOOTER_NOTES}}</div>
</body>
</html>"""

	filled = template.replace("{{COURSE_TITLE}}", course_title)
	filled = filled.replace("{{SLIDE_TITLE}}", slide_title)
	filled = filled.replace("{{SLIDE_CONTENT}}", slide_content)
	filled = filled.replace("{{FOOTER_NOTES}}", footer_notes)
	return filled

def get_next_slide_number(slides_dir):
	"""
	Finds highest existing slide number to support resuming generation.
	"""
	# Find all slide files and get the highest number
	slide_files = glob.glob(str(slides_dir / "slide_*.html"))
	if not slide_files:
		return 1
	
	numbers = [int(re.search(r'slide_(\d+)\.html', f).group(1)) for f in slide_files]
	return max(numbers) + 1

def main():
	parser = argparse.ArgumentParser(description='Generate slides from course outline')
	parser.add_argument('--course-id', help='Unique identifier for the course')
	parser.add_argument('--config', help='Path to course configuration file')
	parser.add_argument('--base-dir', default='./slidegen_courses', help='Base directory for all courses')
	parser.add_argument('--test-mode', action='store_true', help='Generate only 5 slides for testing')
	parser.add_argument('--list-courses', action='store_true', help='List all available courses')
	args = parser.parse_args()

	# Initialize course manager
	course_manager = CourseManager(args.base_dir)

	# Handle list-courses command
	if args.list_courses:
		courses = course_manager.list_courses()
		if not courses:
			print("\nNo courses found. Create a new course with --course-id and --config options.")
			return

		print("\nAvailable Courses:")
		print("-" * 80)
		print(f"{'ID':<20} {'Title':<40} {'Slides':<10}")
		print("-" * 80)
		for course in courses:
			print(f"{course['id']:<20} {course['title'][:38]:<40} {course['slides_count']:<10}")
		print("\nTo generate slides for a course, use:")
		print("python generate_slides.py --course-id <course_id>")
		return

	if not args.course_id:
		print("Error: --course-id is required")
		return

	# Create course directory structure
	course_dir = course_manager.create_course_directory(args.course_id)

	# If config file is provided, copy it to the course directory
	if args.config:
		config_src = Path(args.config)
		if not config_src.exists():
			print(f"Error: Config file {args.config} not found")
			return
		config_dest = course_dir / "config" / "course_config.txt"
		if not config_dest.exists():
			import shutil
			shutil.copy2(config_src, config_dest)

	# Set up paths
	config_file = course_dir / "config" / "course_config.txt"
	slides_dir = course_dir / "slides"
	temp_dir = course_dir / "temp"

	if not Path(config_file).exists():
		print(f"Error: Course configuration file not found: {config_file}")
		sys.exit(1)

	# Parse course configuration
	course_title, topics = parse_config(config_file)

	# Save course info
	course_info = {
		"id": args.course_id,
		"title": course_title,
		"config_file": str(config_file),
		"total_topics": len(topics)
	}
	with open(course_dir / "config" / "course_info.json", 'w') as f:
		json.dump(course_info, f, indent=2)

	# Get next slide number
	next_slide = get_next_slide_number(slides_dir)

	# Initialize summary stack for context
	summary_stack = []

	# Read previous summaries if resuming
	summary_file = slides_dir / "summaries.json"
	if summary_file.exists():
		with open(summary_file, 'r') as f:
			summary_stack = json.load(f)

	# Generate slides
	try:
		for i, topic in enumerate(topics[next_slide-1:], start=next_slide):
			if args.test_mode and i > 5:
				break

			print(f"\nGenerating slide {i} for topic: {topic}")

			# Generate slide content
			prompt = generate_slide_prompt(course_title, summary_stack, topic)
			response_file = temp_dir / f"response_{i}.txt"

			success = run_prompt_through_anthropic(prompt, response_file)
			if not success:
				print(f"Error generating slide {i}")
				continue

			# Read response
			with open(response_file, 'r') as f:
				slide_content = f.read().strip()

			if slide_content == "TOPIC_CLARIFICATION_NEEDED":
				print(f"Warning: AI needs clarification for topic: {topic}")
				continue

			# Split content if needed and create slides
			slide_parts = slide_content.split("<!--SPLIT_SLIDE_HERE-->")
			for j, part in enumerate(slide_parts, start=1):
				slide_number = f"{i:03d}"
				if len(slide_parts) > 1:
					slide_number += f"_{j}"

				slide_file = slides_dir / f"slide_{slide_number}.html"
				with open(slide_file, 'w') as f:
					f.write(insert_into_template(course_title, topic, part.strip()))

				# Generate and save summary
				summary_prompt = summarize_slide_prompt(part.strip())
				summary_response_file = temp_dir / f"summary_{slide_number}.txt"

				if run_prompt_through_anthropic(summary_prompt, summary_response_file):
					with open(summary_response_file, 'r') as f:
						summary = f.read().strip()
						if summary != "CONTENT_CLARIFICATION_NEEDED":
							summary_stack.append(summary)

							# Save updated summaries
							with open(summary_file, 'w') as f:
								json.dump(summary_stack, f, indent=2)

			# Clean up temporary files
			for temp_file in temp_dir.glob(f"*_{i}*.txt"):
				temp_file.unlink()

	except KeyboardInterrupt:
		print("\nGeneration interrupted. Progress has been saved.")
		print(f"Resume from slide {next_slide} next time.")
		sys.exit(0)

	print("\nSlide generation complete!")
	print(f"Generated slides are in: {slides_dir}")

if __name__ == "__main__":
	main()
# end generate_slides.py