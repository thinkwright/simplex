// Common JavaScript functions shared across all pages
document.addEventListener('DOMContentLoaded', () => {
    // Copy code to clipboard
    window.copyCode = function(button) {
        const codeBlock = button.closest('.code-example') || button.closest('pre');
        const code = codeBlock.querySelector('code') || codeBlock;
        const text = code.textContent || code.innerText;

        navigator.clipboard.writeText(text).then(() => {
            const originalText = button.textContent;
            button.textContent = 'Copied!';
            button.classList.add('copied');
            setTimeout(() => {
                button.textContent = originalText;
                button.classList.remove('copied');
            }, 2000);
        }).catch(err => {
            console.error('Failed to copy:', err);
            button.textContent = 'Error';
        });
    };

    // Toggle collapsible code blocks
    window.toggleCodeBlock = function(button) {
        var container = button.closest('.collapsible-code');
        if (container.classList.contains('expanded')) {
            container.classList.remove('expanded');
            button.textContent = 'Show full specification';
        } else {
            container.classList.add('expanded');
            button.textContent = 'Collapse';
        }
    };

    // Smooth scroll for anchor links (offset for fixed nav)
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                smoothScrollTo(target);
            }
        });
    });

    // Active nav link highlighting
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(link => {
        const linkPath = link.getAttribute('href');
        if (linkPath === currentPath || (linkPath !== '/' && currentPath.startsWith(linkPath))) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });

    // Document page table of contents (if exists)
    const tocContainer = document.querySelector('.doc-container');
    if (tocContainer) {
        createTableOfContents();
    }

});

// Smooth scroll with offset for fixed navbar
function smoothScrollTo(element) {
    const navHeight = document.querySelector('.nav').offsetHeight;
    const top = element.getBoundingClientRect().top + window.pageYOffset - navHeight - 20;
    window.scrollTo({ top, behavior: 'smooth' });
}

// Create compact inline table of contents for document pages
function createTableOfContents() {
    const sections = document.querySelectorAll('.doc-section h2');
    if (sections.length < 2) return;

    const nav = document.createElement('nav');
    nav.className = 'spec-toc';

    const strong = document.createElement('strong');
    strong.textContent = 'Contents ';
    nav.appendChild(strong);

    const ul = document.createElement('ul');
    sections.forEach((section, index) => {
        const id = section.parentElement.id || `section-${index}`;
        section.parentElement.id = id;

        const li = document.createElement('li');
        const a = document.createElement('a');
        a.href = `#${id}`;
        a.textContent = section.textContent;
        a.addEventListener('click', (e) => {
            e.preventDefault();
            smoothScrollTo(section);
        });
        li.appendChild(a);
        ul.appendChild(li);
    });
    nav.appendChild(ul);

    const docContainer = document.querySelector('.doc-container');
    const intro = docContainer.querySelector('.doc-intro');
    if (intro) {
        intro.parentNode.insertBefore(nav, intro.nextSibling);
    } else {
        docContainer.insertBefore(nav, docContainer.firstChild.nextSibling);
    }
}