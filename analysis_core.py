# analysis_core.py
import os
from finance_reports_displayname_fixed import ai_interface

# analysis_core.py (continued)
def generate_user_response(user_message: str, user_id: str = "1", send_pdf: bool = True):
    response = ai_interface(user_message, user_id=user_id)
    summary = response.get("summary", "").strip()
    pdf_path = response.get("pdf")

    pdf_to_send = None
    if pdf_path and os.path.exists(pdf_path):
        pdf_to_send = pdf_path
        if send_pdf:
            # Schedule deletion after sending
            import atexit
            def remove_pdf():
                try:
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)
                        print(f"[INFO] PDF deleted: {pdf_path}")
                except Exception as e:
                    print(f"[WARN] Failed to delete PDF {pdf_path}: {e}")
            atexit.register(remove_pdf)

    return {
        "message": summary,
        "pdf_path": pdf_to_send if not send_pdf else pdf_path
    }

