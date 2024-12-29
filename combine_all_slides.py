import glob
import os
import sys
from pathlib import Path

def find_slides_dir(specified_dir=None):
    if specified_dir:
        slides_dir = Path(specified_dir)
        if slides_dir.exists() and any(slides_dir.glob("slide_*.html")):
            return slides_dir
        print(f"Error: No slides found in {specified_dir}")
        sys.exit(1)
        
    # Look for directories containing slides
    potential_dirs = []
    for dir_path in Path('.').iterdir():
        if dir_path.is_dir() and any(dir_path.glob("slide_*.html")):
            potential_dirs.append(dir_path)
            
    if not potential_dirs:
        print("Error: No directories containing slides found")
        sys.exit(1)
        
    if len(potential_dirs) == 1:
        dir_path = potential_dirs[0]
        response = input(f"Found slides in directory '{dir_path}'. Use this directory? [Y/n] ")
        if response.lower() in ['', 'y', 'yes']:
            return dir_path
        sys.exit(0)
        
    print("Multiple directories with slides found:")
    for i, dir_path in enumerate(potential_dirs, 1):
        print(f"{i}. {dir_path}")
    print("Please specify directory using command line argument")
    sys.exit(1)

# Get slides directory
slides_dir = find_slides_dir(sys.argv[1] if len(sys.argv) > 1 else None)

output_file = slides_dir / "combined_slides.html"
slides = sorted(slides_dir.glob("slide_*.html"))

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
<script>
    document.addEventListener('keydown', function(e) {
        const slides = document.querySelectorAll('.slide-wrapper iframe');
        const currentSlide = document.querySelector(':target') || document.querySelector('#slide_1');
        const currentIndex = parseInt(currentSlide.id.split('_')[1]) - 1;
        
        switch(e.key) {
            case 'ArrowLeft':
            case 'ArrowUp':
                e.preventDefault();
                if (currentIndex > 0) {
                    window.location.hash = `#slide_${currentIndex}`;
                }
                break;
            case 'ArrowRight':
            case 'ArrowDown':
            case ' ':  // Spacebar
                e.preventDefault();
                if (currentIndex < slides.length - 1) {
                    window.location.hash = `#slide_${currentIndex + 2}`;
                }
                break;
            case 'Home':
                e.preventDefault();
                window.location.hash = '#slide_1';
                break;
            case 'End':
                e.preventDefault();
                window.location.hash = `#slide_${slides.length}`;
                break;
        }
    });
</script>
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
    # Use relative path from output file to slide
    rel_path = os.path.relpath(slide, output_file.parent)
    body_slides += f"<h2 id='{slide_id}'>{slide_id}</h2>\n<iframe src='{rel_path}'></iframe>\n\n"

footer = "</div></body></html>"

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(head + middle + body_slides + footer)

print(f"Combined slides written to {output_file}")
