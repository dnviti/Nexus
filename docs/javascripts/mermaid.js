/**
 * Mermaid Integration for Nexus Platform Documentation
 * Handles theme switching and proper initialization
 */

// Initialize Mermaid with theme support
window.addEventListener('DOMContentLoaded', function() {
    // Get current theme from Material theme
    const getCurrentTheme = () => {
        const palette = JSON.parse(localStorage.getItem("__palette") || "{}");
        return palette.index === 1 ? 'dark' : 'light';
    };

    // Mermaid configuration
    const mermaidConfig = {
        startOnLoad: false,
        theme: getCurrentTheme(),
        themeVariables: {
            primaryColor: '#2196f3',
            primaryTextColor: getCurrentTheme() === 'dark' ? '#ffffff' : '#000000',
            primaryBorderColor: '#2196f3',
            lineColor: getCurrentTheme() === 'dark' ? '#64b5f6' : '#1976d2',
            secondaryColor: '#bbdefb',
            tertiaryColor: '#e3f2fd',
            background: getCurrentTheme() === 'dark' ? '#263238' : '#ffffff',
            mainBkg: getCurrentTheme() === 'dark' ? '#37474f' : '#f5f5f5',
            secondBkg: getCurrentTheme() === 'dark' ? '#455a64' : '#eeeeee',
            tertiaryBkg: getCurrentTheme() === 'dark' ? '#546e7a' : '#e0e0e0'
        },
        flowchart: {
            useMaxWidth: true,
            htmlLabels: true,
            curve: 'basis'
        },
        sequence: {
            useMaxWidth: true,
            actorMargin: 50,
            boxMargin: 10,
            boxTextMargin: 5,
            noteMargin: 10,
            messageMargin: 35
        },
        gantt: {
            useMaxWidth: true,
            leftPadding: 75,
            gridLineStartPadding: 35
        },
        journey: {
            useMaxWidth: true,
            leftMargin: 150,
            rightMargin: 150,
            taskMargin: 50,
            taskFontSize: 11,
            taskFontFamily: '"Open Sans", sans-serif',
            sectionFontSize: 11,
            sectionFontFamily: '"Open Sans", sans-serif'
        },
        gitgraph: {
            useMaxWidth: true,
            showBranches: true,
            showCommitLabel: true,
            rotateCommitLabel: false
        }
    };

    // Initialize Mermaid
    mermaid.initialize(mermaidConfig);

    // Function to render all diagrams
    const renderDiagrams = () => {
        const diagrams = document.querySelectorAll('.mermaid');
        diagrams.forEach((diagram, index) => {
            if (!diagram.getAttribute('data-processed')) {
                const id = `mermaid-diagram-${index}-${Date.now()}`;
                diagram.setAttribute('id', id);

                try {
                    mermaid.render(id, diagram.textContent, (svgCode) => {
                        diagram.innerHTML = svgCode;
                        diagram.setAttribute('data-processed', 'true');

                        // Add responsive classes
                        const svg = diagram.querySelector('svg');
                        if (svg) {
                            svg.setAttribute('width', '100%');
                            svg.setAttribute('style', 'max-width: 100%; height: auto;');
                        }
                    });
                } catch (error) {
                    console.error('Mermaid rendering error:', error);
                    diagram.innerHTML = `<div class="mermaid-error">
                        <p><strong>Diagram rendering error:</strong></p>
                        <pre><code>${error.message}</code></pre>
                        <details>
                            <summary>Original diagram code</summary>
                            <pre><code>${diagram.textContent}</code></pre>
                        </details>
                    </div>`;
                }
            }
        });
    };

    // Function to update theme and re-render diagrams
    const updateMermaidTheme = (newTheme) => {
        mermaidConfig.theme = newTheme;
        mermaidConfig.themeVariables.primaryTextColor = newTheme === 'dark' ? '#ffffff' : '#000000';
        mermaidConfig.themeVariables.lineColor = newTheme === 'dark' ? '#64b5f6' : '#1976d2';
        mermaidConfig.themeVariables.background = newTheme === 'dark' ? '#263238' : '#ffffff';
        mermaidConfig.themeVariables.mainBkg = newTheme === 'dark' ? '#37474f' : '#f5f5f5';
        mermaidConfig.themeVariables.secondBkg = newTheme === 'dark' ? '#455a64' : '#eeeeee';
        mermaidConfig.themeVariables.tertiaryBkg = newTheme === 'dark' ? '#546e7a' : '#e0e0e0';

        mermaid.initialize(mermaidConfig);

        // Clear processed flags and re-render
        document.querySelectorAll('.mermaid[data-processed]').forEach(diagram => {
            diagram.removeAttribute('data-processed');
        });
        renderDiagrams();
    };

    // Initial render
    renderDiagrams();

    // Watch for theme changes
    const observeThemeChanges = () => {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'attributes' && mutation.attributeName === 'data-md-color-scheme') {
                    const newTheme = mutation.target.getAttribute('data-md-color-scheme') === 'slate' ? 'dark' : 'light';
                    updateMermaidTheme(newTheme);
                }
            });
        });

        const body = document.body;
        if (body) {
            observer.observe(body, {
                attributes: true,
                attributeFilter: ['data-md-color-scheme']
            });
        }

        // Also watch for palette changes in localStorage
        window.addEventListener('storage', (e) => {
            if (e.key === '__palette') {
                const newTheme = getCurrentTheme();
                updateMermaidTheme(newTheme);
            }
        });
    };

    // Start observing theme changes
    observeThemeChanges();

    // Re-render diagrams when navigating (for SPA-like behavior)
    document.addEventListener('DOMContentLoaded', renderDiagrams);

    // Handle instant navigation
    if (typeof app !== 'undefined' && app.document$) {
        app.document$.subscribe(renderDiagrams);
    }

    // Fallback: periodically check for new diagrams
    let renderTimeout;
    const scheduleRender = () => {
        clearTimeout(renderTimeout);
        renderTimeout = setTimeout(() => {
            const unprocessedDiagrams = document.querySelectorAll('.mermaid:not([data-processed])');
            if (unprocessedDiagrams.length > 0) {
                renderDiagrams();
            }
        }, 100);
    };

    // Watch for DOM changes
    const contentObserver = new MutationObserver(scheduleRender);
    contentObserver.observe(document.body, {
        childList: true,
        subtree: true
    });
});

// Export for potential external use
window.nexusMermaid = {
    renderDiagrams: () => {
        const diagrams = document.querySelectorAll('.mermaid:not([data-processed])');
        diagrams.forEach((diagram, index) => {
            const id = `mermaid-diagram-${index}-${Date.now()}`;
            diagram.setAttribute('id', id);

            try {
                mermaid.render(id, diagram.textContent, (svgCode) => {
                    diagram.innerHTML = svgCode;
                    diagram.setAttribute('data-processed', 'true');

                    const svg = diagram.querySelector('svg');
                    if (svg) {
                        svg.setAttribute('width', '100%');
                        svg.setAttribute('style', 'max-width: 100%; height: auto;');
                    }
                });
            } catch (error) {
                console.error('Mermaid rendering error:', error);
                diagram.innerHTML = `<div class="mermaid-error">
                    <p><strong>Diagram rendering error:</strong></p>
                    <pre><code>${error.message}</code></pre>
                </div>`;
            }
        });
    }
};
