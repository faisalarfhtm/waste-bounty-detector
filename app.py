from datetime import datetime
from utils import current_user

@app.context_processor
def inject_globals():
    return {
        "user": current_user(),
        "current_year": datetime.now().year,
    }
