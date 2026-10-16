"""Run the unified Sale/Orders generation pipeline."""

try:
    from .sale_order_engine import main
except ImportError:
    from sale_order_engine import main


if __name__ == "__main__":
    main()
