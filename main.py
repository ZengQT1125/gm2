import asyncio
import json
from datetime import datetime, timezone
import os
import base64
import re
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Depends, Header, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
import time
import uuid
import logging

from gemini_webapi import GeminiClient, set_log_level
from gemini_webapi.constants import Model

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
set_log_level("INFO")

app = FastAPI(title="Gemini API FastAPI Server")

# Add CORS middleware
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# Mount static files
try:
	app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
	logger.warning(f"Could not mount static files: {e}")

# Global client
gemini_client = None

# Authentication credentials
SECURE_1PSID = os.environ.get("SECURE_1PSID", "")
SECURE_1PSIDTS = os.environ.get("SECURE_1PSIDTS", "")
API_KEY = os.environ.get("API_KEY", "")
HF_TOKEN = os.environ.get("HF_TOKEN", "")  # Hugging Face token for private spaces

# Print debug info at startup
if not SECURE_1PSID or not SECURE_1PSIDTS:
	logger.warning("⚠️ Gemini API credentials are not set or empty! Please check your environment variables.")
	logger.warning("Make sure SECURE_1PSID and SECURE_1PSIDTS are correctly set in your .env file or environment.")
	logger.warning("If using Docker, ensure the .env file is correctly mounted and formatted.")
	logger.warning("Example format in .env file (no quotes):")
	logger.warning("SECURE_1PSID=your_secure_1psid_value_here")
	logger.warning("SECURE_1PSIDTS=your_secure_1psidts_value_here")
else:
	# Only log the first few characters for security
	logger.info(f"Credentials found. SECURE_1PSID starts with: {SECURE_1PSID[:5]}...")
	logger.info(f"Credentials found. SECURE_1PSIDTS starts with: {SECURE_1PSIDTS[:5]}...")

if not API_KEY and not HF_TOKEN:
	logger.warning("⚠️ Neither API_KEY nor HF_TOKEN is set! API authentication will not work.")
	logger.warning("Make sure API_KEY or HF_TOKEN is correctly set in your .env file or environment.")
	logger.warning("For Hugging Face private spaces, set HF_TOKEN to your Hugging Face access token.")
else:
	if API_KEY:
		logger.info(f"API_KEY found. API_KEY starts with: {API_KEY[:5]}...")
	if HF_TOKEN:
		logger.info(f"HF_TOKEN found. HF_TOKEN starts with: {HF_TOKEN[:5]}...")


def correct_markdown(md_text: str) -> str:
	"""
	修正Markdown文本，移除Google搜索链接包装器，并根据显示文本简化目标URL。
	"""
	def simplify_link_target(text_content: str) -> str:
		match_colon_num = re.match(r"([^:]+:\d+)", text_content)
		if match_colon_num:
			return match_colon_num.group(1)
		return text_content

	def replacer(match: re.Match) -> str:
		outer_open_paren = match.group(1)
		display_text = match.group(2)

		new_target_url = simplify_link_target(display_text)
		new_link_segment = f"[`{display_text}`]({new_target_url})"

		if outer_open_paren:
			return f"{outer_open_paren}{new_link_segment})"
		else:
			return new_link_segment
	pattern = r"(\()?\[`([^`]+?)`\]\((https://www.google.com/search\?q=)(.*?)(?<!\\)\)\)*(\))?"
	
	fixed_google_links = re.sub(pattern, replacer, md_text)
	# fix wrapped markdownlink
	pattern = r"`(\[[^\]]+\]\([^\)]+\))`"
	return re.sub(pattern, r'\1', fixed_google_links)


# Pydantic models for API requests and responses
class ContentItem(BaseModel):
	type: str
	text: Optional[str] = None
	image_url: Optional[Dict[str, str]] = None


class Message(BaseModel):
	role: str
	content: Union[str, List[ContentItem]]
	name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
	model: str
	messages: List[Message]
	temperature: Optional[float] = 0.7
	top_p: Optional[float] = 1.0
	n: Optional[int] = 1
	stream: Optional[bool] = False
	max_tokens: Optional[int] = None
	presence_penalty: Optional[float] = 0
	frequency_penalty: Optional[float] = 0
	user: Optional[str] = None


class Choice(BaseModel):
	index: int
	message: Message
	finish_reason: str


class Usage(BaseModel):
	prompt_tokens: int
	completion_tokens: int
	total_tokens: int


class ChatCompletionResponse(BaseModel):
	id: str
	object: str = "chat.completion"
	created: int
	model: str
	choices: List[Choice]
	usage: Usage


class ModelData(BaseModel):
	id: str
	object: str = "model"
	created: int
	owned_by: str = "google"


class ModelList(BaseModel):
	object: str = "list"
	data: List[ModelData]


# Authentication dependency - Updated for Hugging Face Spaces
async def verify_api_key(
	authorization: str = Header(None),
	x_api_key: str = Header(None, alias="X-API-Key")
):
	"""
	验证 API 密钥，支持多种认证方式：
	1. Authorization: Bearer TOKEN (传统方式)
	2. X-API-Key: TOKEN (Hugging Face Spaces 推荐方式)
	"""

	# 如果没有设置任何认证令牌，跳过验证（开发模式）
	if not API_KEY and not HF_TOKEN:
		logger.warning("API key validation skipped - no API_KEY or HF_TOKEN set in environment")
		return

	# 优先检查 X-API-Key 头（Hugging Face Spaces 推荐）
	if x_api_key:
		logger.info("Authenticating using X-API-Key header")
		if API_KEY and x_api_key == API_KEY:
			logger.info("Successfully authenticated using X-API-Key with API_KEY")
			return x_api_key
		elif HF_TOKEN and x_api_key == HF_TOKEN:
			logger.info("Successfully authenticated using X-API-Key with HF_TOKEN")
			return x_api_key
		else:
			logger.warning("Invalid API key received in X-API-Key header")
			raise HTTPException(status_code=401, detail="Invalid API key in X-API-Key header")

	# 回退到传统的 Authorization 头
	if authorization:
		logger.info("Authenticating using Authorization header")
		try:
			scheme, token = authorization.split()
			if scheme.lower() != "bearer":
				raise HTTPException(status_code=401, detail="Invalid authentication scheme. Use Bearer token")

			# Check against API_KEY first, then HF_TOKEN
			if API_KEY and token == API_KEY:
				logger.info("Successfully authenticated using Authorization header with API_KEY")
				return token
			elif HF_TOKEN and token == HF_TOKEN:
				logger.info("Successfully authenticated using Authorization header with HF_TOKEN")
				return token
			else:
				logger.warning("Invalid token in Authorization header")
				raise HTTPException(status_code=401, detail="Invalid API key or HF token")
		except ValueError:
			raise HTTPException(status_code=401, detail="Invalid authorization format. Use 'Bearer YOUR_TOKEN'")

	# 如果两种头都没有提供
	raise HTTPException(
		status_code=401,
		detail="Missing authentication. Provide either 'Authorization: Bearer TOKEN' or 'X-API-Key: TOKEN' header"
	)


# Simple error handler middleware
@app.middleware("http")
async def error_handling(request: Request, call_next):
	try:
		return await call_next(request)
	except Exception as e:
		logger.error(f"Request failed: {str(e)}")
		return JSONResponse(status_code=500, content={"error": {"message": str(e), "type": "internal_server_error"}})


# Get list of available models
@app.get("/v1/models")
async def list_models():
	"""返回 gemini_webapi 中声明的模型列表"""
	now = int(datetime.now(tz=timezone.utc).timestamp())
	data = [
		{
			"id": m.model_name,  # 如 "gemini-2.0-flash"
			"object": "model",
			"created": now,
			"owned_by": "google-gemini-web",
		}
		for m in Model
	]
	print(data)
	return {"object": "list", "data": data}


# Helper to convert between Gemini and OpenAI model names
def map_model_name(openai_model_name: str) -> Model:
	"""根据模型名称字符串查找匹配的 Model 枚举值"""
	# 打印所有可用模型以便调试
	all_models = [m.model_name if hasattr(m, "model_name") else str(m) for m in Model]
	logger.info(f"Available models: {all_models}")

	# 首先尝试直接查找匹配的模型名称
	for m in Model:
		model_name = m.model_name if hasattr(m, "model_name") else str(m)
		if openai_model_name.lower() in model_name.lower():
			return m

	# 如果找不到匹配项，使用默认映射
	model_keywords = {
		"gemini-pro": ["pro", "2.0"],
		"gemini-pro-vision": ["vision", "pro"],
		"gemini-flash": ["flash", "2.0"],
		"gemini-1.5-pro": ["1.5", "pro"],
		"gemini-1.5-flash": ["1.5", "flash"],
	}

	# 根据关键词匹配
	keywords = model_keywords.get(openai_model_name, ["pro"])  # 默认使用pro模型

	for m in Model:
		model_name = m.model_name if hasattr(m, "model_name") else str(m)
		if all(kw.lower() in model_name.lower() for kw in keywords):
			return m

	# 如果还是找不到，返回第一个模型
	return next(iter(Model))


# Prepare conversation history from OpenAI messages format
def prepare_conversation(messages: List[Message]) -> tuple:
	conversation = ""
	temp_files = []

	for msg in messages:
		if isinstance(msg.content, str):
			# String content handling
			if msg.role == "system":
				conversation += f"System: {msg.content}\n\n"
			elif msg.role == "user":
				conversation += f"Human: {msg.content}\n\n"
			elif msg.role == "assistant":
				conversation += f"Assistant: {msg.content}\n\n"
		else:
			# Mixed content handling
			if msg.role == "user":
				conversation += "Human: "
			elif msg.role == "system":
				conversation += "System: "
			elif msg.role == "assistant":
				conversation += "Assistant: "

			for item in msg.content:
				if item.type == "text":
					conversation += item.text or ""
				elif item.type == "image_url" and item.image_url:
					# Handle image
					image_url = item.image_url.get("url", "")
					if image_url.startswith("data:image/"):
						# Process base64 encoded image
						try:
							# Extract the base64 part and mime type
							header, base64_data = image_url.split(",", 1)
							mime_type = header.split(":")[1].split(";")[0]

							# Determine file extension
							if "jpeg" in mime_type or "jpg" in mime_type:
								ext = ".jpg"
							elif "png" in mime_type:
								ext = ".png"
							elif "gif" in mime_type:
								ext = ".gif"
							elif "webp" in mime_type:
								ext = ".webp"
							else:
								ext = ".png"  # Default to PNG

							image_data = base64.b64decode(base64_data)

							# Create temporary file to hold the image
							with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
								tmp.write(image_data)
								temp_files.append(tmp.name)
								logger.info(f"Created temporary image file: {tmp.name} (size: {len(image_data)} bytes)")
								# 在对话中添加图片引用
								conversation += f"[Image: {tmp.name}] "
						except Exception as e:
							logger.error(f"Error processing base64 image: {str(e)}")
							# Add text description of the failed image
							conversation += "[Image processing failed] "
					elif image_url.startswith("http"):
						# Handle URL images (download and save)
						try:
							import requests
							response = requests.get(image_url, timeout=10)
							if response.status_code == 200:
								# Determine file extension from content type or URL
								content_type = response.headers.get('content-type', '')
								if "jpeg" in content_type or "jpg" in content_type:
									ext = ".jpg"
								elif "png" in content_type:
									ext = ".png"
								elif "gif" in content_type:
									ext = ".gif"
								elif "webp" in content_type:
									ext = ".webp"
								else:
									ext = ".png"

								with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
									tmp.write(response.content)
									temp_files.append(tmp.name)
									logger.info(f"Downloaded and saved image: {tmp.name} (size: {len(response.content)} bytes)")
									# 在对话中添加图片引用
									conversation += f"[Image from URL: {image_url}] "
							else:
								logger.error(f"Failed to download image from {image_url}: HTTP {response.status_code}")
								conversation += "[Image download failed] "
						except Exception as e:
							logger.error(f"Error downloading image from {image_url}: {str(e)}")
							conversation += "[Image download failed] "
					else:
						logger.warning(f"Unsupported image URL format: {image_url}")
						conversation += "[Unsupported image format] "

			conversation += "\n\n"

	# Add a final prompt for the assistant to respond to
	conversation += "Assistant: "

	return conversation, temp_files


# Dependency to get the initialized Gemini client
async def get_gemini_client():
	global gemini_client
	if gemini_client is None:
		try:
			gemini_client = GeminiClient(SECURE_1PSID, SECURE_1PSIDTS)
			await gemini_client.init(timeout=300)
		except Exception as e:
			logger.error(f"Failed to initialize Gemini client: {str(e)}")
			raise HTTPException(status_code=500, detail=f"Failed to initialize Gemini client: {str(e)}")
	return gemini_client


@app.post("/v1/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest, api_key: str = Depends(verify_api_key)):
	try:
		# 确保客户端已初始化
		global gemini_client
		if gemini_client is None:
			gemini_client = GeminiClient(SECURE_1PSID, SECURE_1PSIDTS)
			await gemini_client.init(timeout=300)
			logger.info("Gemini client initialized successfully")

		# 转换消息为对话格式
		conversation, temp_files = prepare_conversation(request.messages)
		logger.info(f"Prepared conversation: {conversation}")
		logger.info(f"Temp files: {temp_files}")

		# 获取适当的模型
		model = map_model_name(request.model)
		logger.info(f"Using model: {model}")

		# 生成响应
		logger.info("Sending request to Gemini...")
		logger.info(f"Number of image files: {len(temp_files)}")

		if temp_files:
			# With files - 确保文件存在且可读，并转换为 Path 对象
			valid_files = []
			for file_path in temp_files:
				if os.path.exists(file_path):
					file_size = os.path.getsize(file_path)
					logger.info(f"Image file: {file_path}, size: {file_size} bytes")
					# 转换为 Path 对象，这是 gemini-webapi 推荐的方式
					valid_files.append(Path(file_path))
				else:
					logger.error(f"Image file not found: {file_path}")

			if valid_files:
				logger.info(f"Sending {len(valid_files)} image(s) to Gemini")
				try:
					response = await gemini_client.generate_content(conversation, files=valid_files, model=model)
				except Exception as e:
					logger.error(f"Error sending images to Gemini: {str(e)}")
					logger.info("Falling back to text-only request")
					response = await gemini_client.generate_content(conversation, model=model)
			else:
				logger.warning("No valid image files found, sending text only")
				response = await gemini_client.generate_content(conversation, model=model)
		else:
			# Text only
			logger.info("Sending text-only request to Gemini")
			response = await gemini_client.generate_content(conversation, model=model)

		# 清理临时文件
		for temp_file in temp_files:
			try:
				os.unlink(temp_file)
			except Exception as e:
				logger.warning(f"Failed to delete temp file {temp_file}: {str(e)}")

		# 提取文本响应
		reply_text = ""
		# 提取思考内容
		if hasattr(response, "thoughts"):
		    reply_text += f"<think>{response.thoughts}</think>"
		if hasattr(response, "text"):
			reply_text += response.text
		else:
			reply_text += str(response)
		reply_text = reply_text.replace("&lt;","<").replace("\\<","<").replace("\\_","_").replace("\\>",">")
		reply_text = correct_markdown(reply_text)
		
		logger.info(f"Response: {reply_text}")

		if not reply_text or reply_text.strip() == "":
			logger.warning("Empty response received from Gemini")
			reply_text = "服务器返回了空响应。请检查 Gemini API 凭据是否有效。"

		# 创建响应对象
		completion_id = f"chatcmpl-{uuid.uuid4()}"
		created_time = int(time.time())

		# 检查客户端是否请求流式响应
		if request.stream:
			# 实现流式响应
			async def generate_stream():
				# 创建 SSE 格式的流式响应
				# 先发送开始事件
				data = {
					"id": completion_id,
					"object": "chat.completion.chunk",
					"created": created_time,
					"model": request.model,
					"choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
				}
				yield f"data: {json.dumps(data)}\n\n"

				# 模拟流式输出 - 将文本按字符分割发送
				for char in reply_text:
					data = {
						"id": completion_id,
						"object": "chat.completion.chunk",
						"created": created_time,
						"model": request.model,
						"choices": [{"index": 0, "delta": {"content": char}, "finish_reason": None}],
					}
					yield f"data: {json.dumps(data)}\n\n"
					# 可选：添加短暂延迟以模拟真实的流式输出
					await asyncio.sleep(0.01)

				# 发送结束事件
				data = {
					"id": completion_id,
					"object": "chat.completion.chunk",
					"created": created_time,
					"model": request.model,
					"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
				}
				yield f"data: {json.dumps(data)}\n\n"
				yield "data: [DONE]\n\n"

			return StreamingResponse(generate_stream(), media_type="text/event-stream")
		else:
			# 非流式响应（原来的逻辑）
			result = {
				"id": completion_id,
				"object": "chat.completion",
				"created": created_time,
				"model": request.model,
				"choices": [{"index": 0, "message": {"role": "assistant", "content": reply_text}, "finish_reason": "stop"}],
				"usage": {
					"prompt_tokens": len(conversation.split()),
					"completion_tokens": len(reply_text.split()),
					"total_tokens": len(conversation.split()) + len(reply_text.split()),
				},
			}

			logger.info(f"Returning response: {result}")
			return result

	except Exception as e:
		logger.error(f"Error generating completion: {str(e)}", exc_info=True)
		raise HTTPException(status_code=500, detail=f"Error generating completion: {str(e)}")


@app.post("/v1/chat/completions/upload")
async def create_chat_completion_with_upload(
	message: str = Form(...),
	model: str = Form(default="gemini-2.0-flash"),
	temperature: float = Form(default=0.7),
	max_tokens: int = Form(default=1000),
	files: List[UploadFile] = File(default=[]),
	api_key: str = Depends(verify_api_key)
):
	"""
	支持文件上传的聊天完成端点
	可以直接上传图片文件（PNG、JPG、GIF、WebP等）
	"""
	try:
		# 确保客户端已初始化
		global gemini_client
		if gemini_client is None:
			gemini_client = GeminiClient(SECURE_1PSID, SECURE_1PSIDTS)
			await gemini_client.init(timeout=300)
			logger.info("Gemini client initialized successfully")

		# 处理上传的文件
		temp_files = []
		content_items = [{"type": "text", "text": message}]

		for uploaded_file in files:
			if uploaded_file.filename:
				logger.info(f"Processing uploaded file: {uploaded_file.filename}")

				# 检查文件类型
				content_type = uploaded_file.content_type or ""
				if not content_type.startswith("image/"):
					logger.warning(f"Skipping non-image file: {uploaded_file.filename}")
					continue

				# 读取文件内容
				file_content = await uploaded_file.read()
				logger.info(f"Read {len(file_content)} bytes from {uploaded_file.filename}")

				# 确定文件扩展名
				filename = uploaded_file.filename.lower()
				if filename.endswith(('.jpg', '.jpeg')):
					ext = '.jpg'
				elif filename.endswith('.png'):
					ext = '.png'
				elif filename.endswith('.gif'):
					ext = '.gif'
				elif filename.endswith('.webp'):
					ext = '.webp'
				else:
					ext = '.png'  # 默认

				# 创建临时文件
				with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
					tmp.write(file_content)
					temp_files.append(Path(tmp.name))
					logger.info(f"Saved uploaded file to: {tmp.name}")

				# 同时创建 base64 版本用于 content
				base64_data = base64.b64encode(file_content).decode('utf-8')
				mime_type = content_type if content_type else f"image/{ext[1:]}"
				data_url = f"data:{mime_type};base64,{base64_data}"

				content_items.append({
					"type": "image_url",
					"image_url": {"url": data_url}
				})

		# 构建消息
		messages = [{
			"role": "user",
			"content": content_items
		}]

		# 准备对话
		conversation, additional_temp_files = prepare_conversation(messages)
		temp_files.extend([Path(f) for f in additional_temp_files])

		logger.info(f"Prepared conversation with {len(temp_files)} files")

		# 获取模型
		gemini_model = map_model_name(model)
		logger.info(f"Using model: {gemini_model}")

		# 生成响应
		if temp_files:
			logger.info(f"Sending request with {len(temp_files)} files to Gemini")
			try:
				response = await gemini_client.generate_content(conversation, files=temp_files, model=gemini_model)
			except Exception as e:
				logger.error(f"Error sending files to Gemini: {str(e)}")
				logger.info("Falling back to text-only request")
				response = await gemini_client.generate_content(conversation, model=gemini_model)
		else:
			logger.info("Sending text-only request to Gemini")
			response = await gemini_client.generate_content(conversation, model=gemini_model)

		# 清理临时文件
		for temp_file in temp_files:
			try:
				if temp_file.exists():
					temp_file.unlink()
			except Exception as e:
				logger.warning(f"Failed to delete temp file {temp_file}: {str(e)}")

		# 提取响应文本
		reply_text = ""
		if hasattr(response, "thoughts"):
			reply_text += f"<think>{response.thoughts}</think>"
		if hasattr(response, "text"):
			reply_text += response.text
		else:
			reply_text += str(response)

		reply_text = reply_text.replace("&lt;","<").replace("\\<","<").replace("\\_","_").replace("\\>",">")
		reply_text = correct_markdown(reply_text)

		if not reply_text or reply_text.strip() == "":
			reply_text = "服务器返回了空响应。请检查 Gemini API 凭据是否有效。"

		# 创建响应
		completion_id = f"chatcmpl-{uuid.uuid4()}"
		created_time = int(time.time())

		result = {
			"id": completion_id,
			"object": "chat.completion",
			"created": created_time,
			"model": model,
			"choices": [{
				"index": 0,
				"message": {
					"role": "assistant",
					"content": reply_text
				},
				"finish_reason": "stop"
			}],
			"usage": {
				"prompt_tokens": len(conversation.split()),
				"completion_tokens": len(reply_text.split()),
				"total_tokens": len(conversation.split()) + len(reply_text.split()),
			},
		}

		logger.info(f"Upload endpoint returning response for {len(files)} files")
		return result

	except Exception as e:
		logger.error(f"Error in upload endpoint: {str(e)}", exc_info=True)
		raise HTTPException(status_code=500, detail=f"Error processing upload: {str(e)}")


@app.get("/")
async def root():
	return {"status": "online", "message": "Gemini API FastAPI Server is running"}


@app.get("/test")
async def test_page():
	"""返回图片上传测试页面"""
	try:
		# 检查文件是否存在
		import os
		file_path = "static/upload_test.html"
		if os.path.exists(file_path):
			return FileResponse(file_path)
		else:
			# 如果文件不存在，返回内联 HTML
			html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>图片上传测试 - Gemini API</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }
        input, textarea, select {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
            box-sizing: border-box;
        }
        textarea {
            height: 100px;
            resize: vertical;
        }
        .file-upload {
            border: 2px dashed #ddd;
            padding: 20px;
            text-align: center;
            border-radius: 5px;
            cursor: pointer;
            transition: border-color 0.3s;
        }
        .file-upload:hover {
            border-color: #007bff;
        }
        button {
            background-color: #007bff;
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            width: 100%;
            margin-top: 10px;
        }
        button:hover {
            background-color: #0056b3;
        }
        button:disabled {
            background-color: #ccc;
            cursor: not-allowed;
        }
        .response {
            margin-top: 20px;
            padding: 15px;
            border-radius: 5px;
            white-space: pre-wrap;
        }
        .response.success {
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .response.error {
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
        .file-info {
            margin-top: 10px;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 5px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🖼️ Gemini 图片识别测试</h1>

        <form id="uploadForm">
            <div class="form-group">
                <label for="token">HF Token:</label>
                <input type="password" id="token" name="token" placeholder="输入你的 Hugging Face Token" required>
            </div>

            <div class="form-group">
                <label for="message">问题:</label>
                <textarea id="message" name="message" placeholder="例如：这是什么？请描述这张图片。" required>这是什么？</textarea>
            </div>

            <div class="form-group">
                <label for="model">模型:</label>
                <select id="model" name="model">
                    <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
                    <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
                    <option value="gemini-2.5-pro">Gemini 2.5 Pro</option>
                </select>
            </div>

            <div class="form-group">
                <label>上传图片:</label>
                <div class="file-upload" id="fileUpload">
                    <p>点击选择图片文件或拖拽到这里</p>
                    <p style="font-size: 14px; color: #666;">支持 PNG, JPG, GIF, WebP 格式</p>
                    <input type="file" id="files" name="files" multiple accept="image/*" style="display: none;">
                </div>
                <div id="fileInfo" class="file-info" style="display: none;"></div>
            </div>

            <button type="submit" id="submitBtn">🚀 发送请求</button>
        </form>

        <div id="response" class="response" style="display: none;"></div>
    </div>

    <script>
        const fileUpload = document.getElementById('fileUpload');
        const fileInput = document.getElementById('files');
        const fileInfo = document.getElementById('fileInfo');
        const form = document.getElementById('uploadForm');
        const submitBtn = document.getElementById('submitBtn');
        const responseDiv = document.getElementById('response');

        fileUpload.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', handleFiles);

        fileUpload.addEventListener('dragover', (e) => {
            e.preventDefault();
            fileUpload.style.borderColor = '#007bff';
        });

        fileUpload.addEventListener('dragleave', () => {
            fileUpload.style.borderColor = '#ddd';
        });

        fileUpload.addEventListener('drop', (e) => {
            e.preventDefault();
            fileUpload.style.borderColor = '#ddd';
            fileInput.files = e.dataTransfer.files;
            handleFiles();
        });

        function handleFiles() {
            const files = fileInput.files;
            if (files.length > 0) {
                let info = `已选择 ${files.length} 个文件:\\n`;
                for (let i = 0; i < files.length; i++) {
                    const file = files[i];
                    info += `• ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)\\n`;
                }
                fileInfo.textContent = info;
                fileInfo.style.display = 'block';
            } else {
                fileInfo.style.display = 'none';
            }
        }

        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            const token = document.getElementById('token').value;
            const message = document.getElementById('message').value;
            const model = document.getElementById('model').value;
            const files = fileInput.files;

            if (!token) {
                alert('请输入 HF Token');
                return;
            }

            if (files.length === 0) {
                alert('请选择至少一张图片');
                return;
            }

            submitBtn.disabled = true;
            submitBtn.textContent = '🔄 处理中...';
            responseDiv.style.display = 'block';
            responseDiv.className = 'response';
            responseDiv.textContent = '正在上传图片并分析，请稍候...';

            try {
                const formData = new FormData();
                formData.append('message', message);
                formData.append('model', model);

                for (let i = 0; i < files.length; i++) {
                    formData.append('files', files[i]);
                }

                const response = await fetch('/v1/chat/completions/upload', {
                    method: 'POST',
                    headers: {
                        'X-API-Key': token
                    },
                    body: formData
                });

                const result = await response.json();

                if (response.ok) {
                    responseDiv.className = 'response success';
                    responseDiv.textContent = result.choices[0].message.content;
                } else {
                    responseDiv.className = 'response error';
                    responseDiv.textContent = `错误: ${result.detail || result.error || '未知错误'}`;
                }
            } catch (error) {
                responseDiv.className = 'response error';
                responseDiv.textContent = `网络错误: ${error.message}`;
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = '🚀 发送请求';
            }
        });
    </script>
</body>
</html>
			"""
			from fastapi.responses import HTMLResponse
			return HTMLResponse(content=html_content)
	except Exception as e:
		return {"error": "Test page not found", "detail": str(e)}


if __name__ == "__main__":
	import uvicorn

	uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level="info")
