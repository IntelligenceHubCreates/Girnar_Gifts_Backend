from app.settings import settings
import cloudinary
import cloudinary.uploader
import cloudinary.api

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret
)

async def upload_images(file_paths):
    uploaded_images = []
    for file_path in file_paths:
        try:
            file_content = await file_path.read()
            response = cloudinary.uploader.upload(
                file_content, folder=f"{settings.cloudinary_folder}/products",
            )
            uploaded_images.append({
                "url": response["secure_url"],
                "public_id": response["public_id"]
            })
            print(f"Uploaded successfully: {response['secure_url']}")
        except Exception as e:
            uploaded_images.append({
                "url": str(e),
                "public_id": "Got_Error"
            })
            print(f"Failed to upload: {str(e)}")
    return uploaded_images