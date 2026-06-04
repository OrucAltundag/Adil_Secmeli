# Automated smoke test for AHPWeightPage
import logging
import traceback
import tkinter as tk
from pathlib import Path

logfile = Path('logs/ahp_auto_test.log')
logfile.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=str(logfile), level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')

try:
    logging.info('Starting AHP UI smoke test')
    root = tk.Tk()
    root.withdraw()
    from app.ui.tabs.ahp_weight_page import AHPWeightPage

    page = AHPWeightPage(root)
    logging.info('AHPWeightPage instantiated')

    try:
        page.refresh()
        logging.info('Called refresh()')
    except Exception as e:
        logging.exception('refresh() raised')

    ids = getattr(page, '_profile_list_ids', [])
    logging.info(f'Found profile ids: {ids}')

    if ids:
        pid = ids[0]
        try:
            page._select_profile_by_id(pid)
            logging.info(f'selected profile id {pid}')
        except Exception:
            logging.exception('select_profile_by_id failed')

        try:
            page._edit_selected_in_tab2()
            logging.info('edit_selected_in_tab2 executed')
        except Exception:
            logging.exception('edit_selected_in_tab2 failed')

        try:
            page.calculate_current_matrix()
            logging.info('calculate_current_matrix executed')
        except Exception:
            logging.exception('calculate_current_matrix failed')

    else:
        logging.warning('No profiles found; skipping selection/edit tests')

    # Dump some internal state for inspection
    try:
        logging.info('Current weights: %s', getattr(page, '_current_weights', {}))
        logging.info('Criterion keys: %s', getattr(page, '_criterion_keys', []))
    except Exception:
        logging.exception('failed to read internal state')

    root.destroy()
    logging.info('AHP UI smoke test completed')
except Exception:
    logging.exception('Unexpected error in AHP UI smoke test')
    raise
