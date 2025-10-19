from app.setup_utils.load_initial_gmt import run_initial_gmt_setup
from app.setup_utils.rebuild_db_files import rebuild_db_files

if __name__ == "__main__":
    run_initial_gmt_setup()

    rebuild_db_files()
