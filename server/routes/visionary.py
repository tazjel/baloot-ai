"""
Visionary Studio routes: video ingest, dataset image serving, verification.
"""
import os
from py4web import action, request, response
from server.common import logger


@action('api/visionary/ingest', method=['POST', 'OPTIONS'])
def visionary_ingest():
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    if request.method == 'OPTIONS':
        return ""

    try:
        from server.settings import UPLOAD_FOLDER
        from game_engine.visionary.visionary import DatasetGenerator

        file_storage = request.files.get('file')
        url = request.forms.get('url')

        ingest_dir = os.path.join(UPLOAD_FOLDER, 'ingest')
        os.makedirs(ingest_dir, exist_ok=True)

        target_path = None

        if file_storage:
            filename = file_storage.filename or "uploaded_video.mp4"
            target_path = os.path.join(ingest_dir, filename)
            file_storage.save(target_path)
            logger.info(f"[VISIONARY] Saved uploaded file to {target_path}")

        elif url:
            import yt_dlp
            logger.info(f"[VISIONARY] Downloading from URL: {url}")

            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'outtmpl': os.path.join(ingest_dir, '%(title)s.%(ext)s'),
                'noplaylist': True,
                'quiet': True
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    target_path = filename
                    logger.info(f"[VISIONARY] Downloaded video to {target_path}")
            except Exception as dl_err:
                logger.error(f"[VISIONARY] yt-dlp failed: {dl_err}")
                return {"status": "error", "message": f"Download failed: {str(dl_err)}"}

        else:
            response.status = 400
            return {"error": "No file or URL provided"}

        if not target_path or not os.path.exists(target_path):
            return {"status": "error", "message": "File processing failed or file not found"}

        dataset_gen = DatasetGenerator(output_dir=os.path.join(UPLOAD_FOLDER, 'dataset'))
        dataset_gen.process_video_for_training(target_path, interval=1.0)

        return {
            "status": "success",
            "message": "Video processed. Frames extracted to dataset/images.",
            "path": os.path.basename(target_path)
        }

    except Exception as e:
        logger.error(f"Visionary Ingest Failed: {e}")
        import traceback
        traceback.print_exc()
        response.status = 500
        return {"error": str(e)}


@action('api/visionary/dataset/image/<filename>', method=['GET'])
def get_dataset_image(filename):
    """Serves images from the dataset directory."""
    from server.settings import UPLOAD_FOLDER

    if '..' in filename or filename.startswith('/') or '\\' in filename:
        response.status = 400
        return "Invalid filename"

    dataset_dir = os.path.join(UPLOAD_FOLDER, 'dataset', 'images', 'train')
    file_path = os.path.join(dataset_dir, filename)

    if not os.path.exists(file_path):
        response.status = 404
        return "File not found"

    with open(file_path, 'rb') as f:
        return f.read()


@action('api/visionary/verify/next', method=['GET'])
def get_next_verification():
    """Returns a random unverified image from the train set."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    from server.settings import UPLOAD_FOLDER
    import random

    dataset_dir = os.path.join(UPLOAD_FOLDER, 'dataset', 'images', 'train')

    if not os.path.exists(dataset_dir):
        return {"error": "Dataset not found"}

    images = [f for f in os.listdir(dataset_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

    if not images:
        return {"done": True, "message": "No images left to verify!"}

    selected = random.choice(images)
    return {"filename": selected, "url": f"/api/visionary/dataset/image/{selected}"}


@action('api/visionary/verify/submit', method=['POST', 'OPTIONS'])
def submit_verification():
    """Handles the user's verdict on an image."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    if request.method == 'OPTIONS':
        return ""

    data = request.json
    filename = data.get('filename')
    verdict = data.get('verdict')
    label = data.get('label')

    from server.settings import UPLOAD_FOLDER
    import shutil

    base_dir = os.path.join(UPLOAD_FOLDER, 'dataset')
    train_dir = os.path.join(base_dir, 'images', 'train')
    verified_dir = os.path.join(base_dir, 'images', 'verified')
    trash_dir = os.path.join(base_dir, 'images', 'trash')

    os.makedirs(verified_dir, exist_ok=True)
    os.makedirs(trash_dir, exist_ok=True)

    src_path = os.path.join(train_dir, filename)

    if not os.path.exists(src_path):
        if os.path.exists(os.path.join(verified_dir, filename)):
            return {"status": "verified (already moved)"}
        return {"error": "Image not found"}

    if verdict == 'invalid':
        dst_path = os.path.join(trash_dir, filename)
        shutil.move(src_path, dst_path)
        return {"status": "moved_to_trash"}

    elif verdict == 'valid' or verdict == 'correction':
        dst_path = os.path.join(verified_dir, filename)
        shutil.move(src_path, dst_path)

        if label:
            label_dir = os.path.join(base_dir, 'labels', 'verified')
            os.makedirs(label_dir, exist_ok=True)
            txt_name = os.path.splitext(filename)[0] + ".txt"
            with open(os.path.join(label_dir, txt_name), 'w') as f:
                f.write(str(label))

        return {"status": "verified"}

    return {"error": "Unknown verdict"}


def bind_visionary(safe_mount):
    """Bind visionary routes to the app."""
    try:
        safe_mount('/api/visionary/dataset/image/<filename>', 'GET', get_dataset_image)
        safe_mount('/api/visionary/verify/next', 'GET', get_next_verification)
        safe_mount('/api/visionary/verify/submit', 'POST', submit_verification)
        safe_mount('/api/visionary/verify/submit', 'OPTIONS', submit_verification)
    except NameError:
        logger.warning("Visionary endpoints not found, skipping mount.")
