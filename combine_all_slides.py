import glob
import os
import sys
from pathlib import Path
import re

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

def extract_slide_content(slide_path):
    with open(slide_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Extract just the slide content between main tags
    match = re.search(r'<main>(.*?)</main>', content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""

# Get slides directory
slides_dir = find_slides_dir(sys.argv[1] if len(sys.argv) > 1 else None)

output_file = slides_dir / "combined_slides.html"
# Use set to remove duplicates and sort to maintain order
slides = sorted(set(slides_dir.glob("slide_*.html")))

head = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>All Slides</title>
<style>
    body { font-family: sans-serif; margin: 0; padding: 0; background: #eee; }
    nav { 
        background: #333; 
        color: #fff; 
        padding: 1rem;
        position: fixed;
        top: 0;
        width: 100%;
        z-index: 100;
    }
    nav a { color: #fff; margin: 0 10px; text-decoration: none; }
    .slide { 
        height: calc(100vh - 4rem);
        padding: 2rem;
        margin: 0;
        box-sizing: border-box;
        display: flex;
        flex-direction: column;
        justify-content: center;
        scroll-snap-align: start;
        background: white;
        margin-bottom: 2px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        position: relative;
    }
    #slides-container {
        margin-top: 4rem;
        scroll-snap-type: y mandatory;
        overflow-y: scroll;
        height: calc(100vh - 4rem);
    }
    .slide-title {
        position: absolute;
        top: 1rem;
        right: 1rem;
        color: #666;
    }
    /* Additional styles from slide template preserved here */
</style>
<script>
    document.addEventListener('DOMContentLoaded', function() {
        const slides = document.querySelectorAll('.slide');
        let currentSlide = 0;

        function goToSlide(index) {
            if (index >= 0 && index < slides.length) {
                currentSlide = index;
                slides[index].scrollIntoView({ behavior: 'smooth' });
                updateHash(index);
            }
        }

        function updateHash(index) {
            // Use replaceState to avoid adding to browser history
            history.replaceState(null, null, `#slide_${index + 1}`);
        }

        // Initialize to hash location or first slide
        const hash = window.location.hash;
        if (hash) {
            const slideNum = parseInt(hash.split('_')[1]) - 1;
            if (!isNaN(slideNum) && slideNum >= 0 && slideNum < slides.length) {
                currentSlide = slideNum;
                slides[currentSlide].scrollIntoView();
            }
        }

        document.addEventListener('keydown', function(e) {
            switch(e.key) {
                case 'ArrowLeft':
                case 'ArrowUp':
                    e.preventDefault();
                    goToSlide(currentSlide - 1);
                    break;
                case 'ArrowRight':
                case 'ArrowDown':
                case ' ':
                    e.preventDefault();
                    goToSlide(currentSlide + 1);
                    break;
                case 'Home':
                    e.preventDefault();
                    goToSlide(0);
                    break;
                case 'End':
                    e.preventDefault();
                    goToSlide(slides.length - 1);
                    break;
            }
        });

        // Update current slide on scroll
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const newIndex = Array.from(slides).indexOf(entry.target);
                    if (newIndex !== currentSlide) {
                        currentSlide = newIndex;
                        updateHash(currentSlide);
                    }
                }
            });
        }, {threshold: 0.5});

        slides.forEach(slide => observer.observe(slide));
    });
</script>
</head>
<body>
<nav>
    <strong>Course Slides</strong>
    <!-- Navigation links to each slide -->
"""

nav_links = []
for i, slide in enumerate(slides, 1):
    slide_name = f"Slide {i}"
    nav_links.append(f'<a href="#slide_{i}">{slide_name}</a>')

nav_section = " | ".join(nav_links)

middle = f"{nav_section}</nav>\n<div id='slides-container'>\n"

body_slides = ""
for i, slide in enumerate(slides, 1):
    slide_id = f"slide_{i}"
    slide_content = extract_slide_content(slide)
    if slide_content:  # Only add slide if it has content
        body_slides += f"""<div class="slide" id="{slide_id}">
    <div class="slide-title">Slide {i}</div>
    {slide_content}
</div>\n\n"""

footer = "</div></body></html>"

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(head + middle + body_slides + footer)

print(f"Combined slides written to {output_file}")

# Potential improvements to consider:
# 1. Add progress bar showing current slide position
# 2. Add touch/swipe support for mobile devices
# 3. Add print stylesheet for PDF export
# 4. Add presenter notes toggle
# 5. Add slide transitions/animations
# 6. Add zoom controls for detailed content
# 7. Add search functionality across all slides
# 8. Add dark mode toggle
# 9. Add table of contents/outline view
# 10. Add support for speaker timer
# 11. Add ability to draw/annotate slides
# 12. Add export to different formats (PDF, PPTX)
# 13. Add support for code syntax highlighting
# 14. Add slide thumbnails view
# 15. Add support for embedded media (video, audio)
