# Convenience targets. Everything works without make too — see README.
PY ?= python

.PHONY: setup engine test demo dashboard db clean

setup:            ## dependencies + engine + book check + smoke run
	$(PY) chess_opening_analyzer/tools/setup_env.py --dashboard

engine:           ## download the Stockfish build for this machine
	$(PY) chess_opening_analyzer/tools/install_stockfish.py

engine-check:     ## report which engine is installed
	$(PY) chess_opening_analyzer/tools/install_stockfish.py --check

test:
	cd chess_opening_analyzer && $(PY) -m pytest tests -q

demo:             ## run the CLI over the bundled sample archive
	cd chess_opening_analyzer && $(PY) -m chessopening --pgn-dir sample_pgns --db local \
		--min-db-games 20 --depth 16 --out-dir out

dashboard:        ## start the API on :8000 (serve chess-dashboard/public separately)
	cd chess-dashboard && $(PY) api_server.py

db:               ## rebuild the opening book (see --help for corpus options)
	cd chess_opening_analyzer && $(PY) tools/build_local_db.py --help

clean:
	rm -rf chess_opening_analyzer/out chess_opening_analyzer/.pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
