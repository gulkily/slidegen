import glob

output_file = "combined_slides.html"
slides = sorted(glob.glob("slide_*.html"))

head = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>All Slides</title>
<style>
    body { font-family: sans-serif; margin:0; padding:0; background:#eee; }
    nav { background:#333; color:#fff; padding:1rem; }
    nav a { color:#fff; margin:0 10px; text-decoration:none; }
    .slide-wrapper { margin: 2rem; }
    .slide-wrapper iframe { width: 100%; height: 90vh; border: none; margin-bottom: 2rem; }
</style>
</head>
<body>
<nav>
    <strong>Course Slides</strong>
    <!-- Navigation links to each slide -->
"""

nav_links = []
for i, slide in enumerate(slides):
    slide_name = f"Slide {i+1}"
    nav_links.append(f'<a href="#slide_{i+1}">{slide_name}</a>')

nav_section = " | ".join(nav_links)

middle = f"{nav_section}</nav>\n<div class='slide-wrapper'>\n"

body_slides = ""
for i, slide in enumerate(slides):
    slide_id = f"slide_{i+1}"
    body_slides += f"<h2 id='{slide_id}'>{slide_id}</h2>\n<iframe src='{slide}'></iframe>\n\n"

footer = "</div></body></html>"

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(head + middle + body_slides + footer)

print(f"Combined slides written to {output_file}")

