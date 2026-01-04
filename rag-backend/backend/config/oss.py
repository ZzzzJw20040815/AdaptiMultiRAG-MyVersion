import os
import boto3
from botocore.client import Config
from backend.config.log import get_logger

logger = get_logger(__name__)

class S3ClientFactory:
    _instance = None
    
    @classmethod
    def get_client(cls):
        """
        获取 S3/MinIO Client 的单例实例
        """
        if cls._instance is None:
            # 从环境变量获取配置
            endpoint = os.getenv('S3_ENDPOINT')
            access_key = os.getenv('S3_ACCESS_KEY')
            secret_key = os.getenv('S3_SECRET_KEY')
            region = os.getenv('S3_REGION', 'us-east-1')

            if not all([endpoint, access_key, secret_key]):
                logger.error("S3配置缺失，请检查.env文件")
                return None

            try:
                # 配置 boto3 client
                cls._instance = boto3.client(
                    's3',
                    endpoint_url=endpoint,
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name=region,
                    config=Config(signature_version='s3v4')
                )
                logger.info(f"S3客户端初始化成功: {endpoint}")
            except Exception as e:
                logger.error(f"S3客户端初始化失败: {e}")
                raise e
                
        return cls._instance

def get_presigned_url_for_upload(bucket: str, key: str, expire_seconds: int = 3600):
    """
    生成上传文件的预签名 URL (PUT)
    """
    client = S3ClientFactory.get_client()
    if not client:
        raise Exception("S3客户端未初始化")

    try:
        # 如果未指定bucket，尝试从环境变量获取
        if not bucket:
            bucket = os.getenv('S3_BUCKET_NAME', 'rag-data')

        # 确保 bucket 存在
        try:
            client.head_bucket(Bucket=bucket)
        except:
            # 尝试创建 bucket (仅用于本地开发环境方便)
            try:
                client.create_bucket(Bucket=bucket)
            except Exception as e:
                logger.warning(f"尝试创建 Bucket {bucket} 失败 (可能已存在或权限不足): {e}")

        # 生成预签名 URL
        url = client.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                'Bucket': bucket,
                'Key': key,
                'ContentType': 'application/octet-stream'
            },
            ExpiresIn=expire_seconds
        )
        
        return {
            "method": "PUT",
            "url": url,
            "headers": {
                "Content-Type": "application/octet-stream"
            }
        }
    except Exception as e:
        logger.error(f"生成上传URL失败: {e}")
        raise e

def get_presigned_url_for_download(bucket: str, key: str, expire_seconds: int = 3600):
    """
    生成下载文件的预签名 URL (GET)
    """
    client = S3ClientFactory.get_client()
    if not client:
        raise Exception("S3客户端未初始化")

    try:
        if not bucket:
            bucket = os.getenv('S3_BUCKET_NAME', 'rag-data')

        url = client.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': bucket,
                'Key': key
            },
            ExpiresIn=expire_seconds
        )
        
        return {
            "method": "GET",
            "url": url
        }
    except Exception as e:
        logger.error(f"生成下载URL失败: {e}")
        raise e

def delete_file(bucket: str, key: str):
    """
    删除文件
    """
    client = S3ClientFactory.get_client()
    if not client:
        raise Exception("S3客户端未初始化")

    try:
        if not bucket:
            bucket = os.getenv('S3_BUCKET_NAME', 'rag-data')
            
        client.delete_object(Bucket=bucket, Key=key)
        logger.info(f"文件删除成功: {bucket}/{key}")
        return True
    except Exception as e:
        logger.error(f"文件删除失败: {e}")
        return False

