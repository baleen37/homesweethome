{
  description = "HomeSweetHome Crawler Boilerplate - Python web crawler with CSV export";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
  }:
    flake-utils.lib.eachDefaultSystem (
      system: let
        pkgs = nixpkgs.legacyPackages.${system};

        # Development shell with all dependencies
        devShell = pkgs.mkShell {
          name = "homesweethome-crawler";

          buildInputs = with pkgs; [
            # Python interpreter
            python311

            # Python package management
            uv

            # System dependencies for Python packages
            openssl
            zlib
            libffi
            readline
            sqlite
            xz

            # For XML parsing (BeautifulSoup)
            libxml2
            libxslt

            # For Playwright browser dependencies
            playwright-driver

            # For image/graphics processing
            cairo
            pango
            gdk-pixbuf
            harfbuzz
            libjpeg
            librsvg

            # Development tools
            ruff
            mypy
            pre-commit
            git

            # Shell utilities
            bash
            coreutils
            findutils
            jq
          ];

          shellHook = ''
            # Set Python path
            export PYTHONPATH="${builtins.toString ./.}/src:$PYTHONPATH"

            # Set Playwright browsers path
            export PLAYWRIGHT_BROWSERS_PATH="${pkgs.playwright-driver.browsers}"

            # Set output directory
            export CRAWLER_OUTPUT_DIR="${builtins.toString ./.}/output"
            mkdir -p "$CRAWLER_OUTPUT_DIR"

            # Initialize uv if needed
            if [ ! -f ".venv/bin/python" ]; then
              echo "🔧 Initializing Python environment with uv..."
              uv venv --python 3.11
            fi

            # Install/update dependencies
            echo "📦 Installing Python dependencies..."
            uv sync --dev

            # Setup git hooks if git repo
            if [ -d ".git" ] && [ ! -f ".git/hooks/pre-commit" ]; then
              echo "🔗 Setting up git hooks..."
              uv run pre-commit install
            fi

            # Activate virtual environment
            source .venv/bin/activate

            # Export environment variables from .env if it exists
            if [ -f ".env" ]; then
              set -a
              source .env
              set +a
            fi

            # Show environment info
            echo ""
            echo "✅ Development environment ready!"
            echo "Python: $(python --version)"
            echo "uv: $(uv --version)"
            echo ""
            echo "📝 Useful commands:"
            echo "  uv run python scripts/main.py --help    # Run crawler"
            echo "  uv run pytest -v                       # Run tests"
            echo "  uv run ruff check .                    # Lint code"
            echo "  uv run mypy src/                       # Type check"
            echo "  uv run ruff format .                   # Format code"
            echo ""
          '';
        };
      in {
        # Development shell only
        devShells.default = devShell;
      }
    );
}