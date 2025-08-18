#!/usr/bin/env python3
"""
Nexus - Main Application Entry Point
A powerful, plugin-based application platform for building modular, scalable applications.
"""

import logging
import sys


# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("nexus.main")

def main():
    """Main application entry point."""
    try:
        # Import here to avoid import issues during startup
        from nexus import create_nexus_app

        # Create the Nexus application
        app = create_nexus_app(
            title="Nexus Application",
            version="1.0.0",
            description="A modular application built with Nexus Framework"
        )

        logger.info("Nexus application created successfully")
        return app.app  # Return the FastAPI app for uvicorn

    except ImportError as e:
        logger.error(f"Failed to import Nexus components: {e}")
        logger.error("Make sure all dependencies are installed: pip install -e .")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to create Nexus application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import uvicorn

    # Get the FastAPI app
    app = main()

    # Run the application
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)
