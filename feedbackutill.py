import streamlit as st
import cv2
import tempfile
import os
import io
import json
import uuid
import shutil
from datetime import datetime
from PIL import Image, ImageDraw

class FeedbackConfig:
    """피드백 공통 설정 클래스"""
    COLOR_MAP = {
        "🔴 빨강": "#FF4B4B",
        "🔵 파랑": "#1C7ED6",
        "🟡 노랑": "#FAB005",
        "🟢 초록": "#2E8B57",
        "🟣 보라": "#9B30FF"
    }

class ImageFeedbackUtils:
    """이미지 피드백 관련 유틸리티 모음"""
    
    @staticmethod
    def draw_pins(base_img: Image.Image, comments: list, active_click: dict = None, active_color: str = "#FF4B4B") -> Image.Image:
        """
        이미지에 기존 코멘트의 핀과 현재 클릭된 위치의 임시 핀을 그립니다.
        """
        img = base_img.copy()
        draw = ImageDraw.Draw(img)
        
        # 저장된 코멘트 핀 그리기
        for comm in comments:
            x, y = comm.get("x", 0), comm.get("y", 0)
            color = comm.get("color", "#FF4B4B")
            draw.ellipse([x-12, y-12, x+12, y+12], fill=color, outline="white", width=2)
            
        # 활성화된 클릭 핀 그리기 (사용자가 방금 클릭한 곳)
        if active_click:
            x, y = active_click.get('x', 0), active_click.get('y', 0)
            draw.ellipse([x-15, y-15, x+15, y+15], outline=active_color, width=3)
            
        return img

    @staticmethod
    def render_feedback_card(file_id: str, comm: dict, save_callback):
        """
        이미지 피드백 카드를 렌더링하고, 수정/삭제 버튼을 포함합니다.
        """
        c_id = comm.get("id")
        if not c_id:
            c_id = str(uuid.uuid4())[:8]
            comm["id"] = c_id
            
        color = comm['color']
        color_name = comm['color_name']
        x, y = comm['x'], comm['y']
        text = comm['text']
        
        edit_key = f"edit_img_{c_id}"
        
        col_content, col_ed, col_del = st.columns([7.5, 1.25, 1.25])
        with col_content:
            st.markdown(f'<div style="background:#FFFDE7; border-left:4px solid {color}; padding:8px; border-radius:4px; margin-bottom:4px;">'
                        f'<span style="font-size:0.8rem; color:#555;">📌 {color_name} 핀 ({x},{y})</span><br>'
                        f'<span style="font-size:1.0rem; color:#000;">{text}</span>'
                        f'</div>', unsafe_allow_html=True)
        with col_ed:
            if st.button("✎", key=f"btn_ed_img_{c_id}", help="수정"):
                st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                st.rerun()
        with col_del:
            if st.button("✕", key=f"btn_del_img_{c_id}", help="삭제"):
                SessionStateManager.delete_image_feedback(file_id, c_id)
                save_callback()
                st.rerun()
                
        if st.session_state.get(edit_key, False):
            new_text = st.text_input("내용 수정", value=text, key=f"in_img_{c_id}", label_visibility="collapsed")
            if st.button("✔ 저장", key=f"save_img_{c_id}"):
                SessionStateManager.update_image_feedback(file_id, c_id, new_text)
                st.session_state[edit_key] = False
                save_callback()
                st.rerun()


class VideoFeedbackUtils:
    """영상 피드백 관련 유틸리티 모음"""
    
    @staticmethod
    @st.cache_data(show_spinner=False)
    def get_video_duration(video_path: str) -> int:
        """비디오 파일의 총 길이(초)를 구합니다."""
        duration = 0
        try:
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            if fps > 0 and frame_count > 0:
                duration = int(frame_count / fps)
            cap.release()
        except Exception:
            pass
        return duration if duration > 0 else 600  # 실패 시 기본값 10분(600초)
    
    
    @staticmethod
    def extract_frame(video_file, target_seconds: int) -> Image.Image:
        """
        업로드된 비디오 파일에서 특정 초(second)의 프레임을 추출하여 PIL Image로 반환합니다.
        OpenCV 및 임시 파일을 활용하여 안전하게 프레임을 가져옵니다.
        """
        video_file.seek(0)
        # 영상을 임시 파일로 저장 (OpenCV는 파일 경로가 필요함)
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        tfile.write(video_file.read())
        tfile.close()
        
        img = None
        try:
            cap = cv2.VideoCapture(tfile.name)
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0: 
                fps = 30
            
            # 목표 시간(초)에 해당하는 프레임 인덱스 계산
            frame_id = int(fps * target_seconds)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
            ret, frame = cap.read()
            
            if ret:
                # BGR을 RGB로 변환 후 PIL 이미지로 바로 생성
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
        finally:
            # 리소스 해제 및 임시 파일 삭제
            if 'cap' in locals():
                cap.release()
            if os.path.exists(tfile.name):
                os.unlink(tfile.name)
                
        return img
        
    @staticmethod
    @st.cache_data(show_spinner=False)
    def extract_frame_from_path(video_path: str, target_seconds: int):
        """
        로컬 디스크에 저장된 비디오 경로에서 바로 프레임을 추출하고 600px로 빠르게 리사이징하여 반환합니다.
        """
        img = None
        try:
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0: 
                fps = 30
            
            frame_id = int(fps * target_seconds)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
            ret, frame = cap.read()
            
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
                # 고속 Bilinear 필터로 600px 리사이징 처리하여 캐싱 크기를 줄이고 렌더링 딜레이 최적화
                if img.width > 600:
                    ratio = 600 / float(img.width)
                    img = img.resize((600, int(img.height * ratio)), Image.Resampling.BILINEAR)
        finally:
            if 'cap' in locals():
                cap.release()
                
        return img
            
    @staticmethod
    def draw_pins_on_frame(base_img: Image.Image, comments: list, target_seconds: int, active_click: dict = None, active_color: str = "#FF4B4B") -> Image.Image:
        """
        추출된 비디오 프레임 이미지에 특정 시간대의 핀과 현재 클릭된 핀을 그립니다.
        """
        img = base_img.copy()
        draw = ImageDraw.Draw(img)
        
        # 저장된 코멘트 핀 그리기 (현재 시간에 해당하는 것만 표시)
        for comm in comments:
            if comm.get("time") == target_seconds:
                x, y = comm.get("x", 0), comm.get("y", 0)
                color = comm.get("color", "#FF4B4B")
                draw.ellipse([x-14, y-14, x+14, y+14], fill=color, outline="white", width=2)
                mins = target_seconds // 60
                secs = target_seconds % 60
                # 흰색 텍스트에 약간의 그림자 효과를 위해 검은색 텍스트를 살짝 어긋나게 그리기
                draw.text((x + 19, y - 5), f"{mins:02d}:{secs:02d}", fill="black")
                draw.text((x + 18, y - 6), f"{mins:02d}:{secs:02d}", fill="white")
                
        # 활성화된 클릭 핀 그리기
        if active_click:
            x, y = active_click.get('x', 0), active_click.get('y', 0)
            draw.ellipse([x-18, y-18, x+18, y+18], outline=active_color, width=3)
            mins = target_seconds // 60
            secs = target_seconds % 60
            draw.text((x + 23, y - 5), f"{mins:02d}:{secs:02d}", fill="black")
            draw.text((x + 22, y - 6), f"{mins:02d}:{secs:02d}", fill="white")
            
        return img

    @staticmethod
    def render_feedback_card(file_id: str, comm: dict, save_callback):
        """
        비디오 피드백 타임라인 카드를 렌더링하고, 수정/삭제 버튼을 포함합니다.
        """
        c_id = comm.get("id")
        if not c_id:
            c_id = str(uuid.uuid4())[:8]
            comm["id"] = c_id
            
        color = comm['color']
        time = comm['time']
        x, y = comm['x'], comm['y']
        text = comm['text']
        
        mins = time // 60
        secs = time % 60
        timestamp = f"{mins:02d}:{secs:02d}"
        
        edit_key = f"edit_vid_{c_id}"
        
        col_content, col_ed, col_del = st.columns([7.5, 1.25, 1.25])
        with col_content:
            st.markdown(f'<div style="background-color: #F0F4FF; border-left: 4px solid {color}; padding: 8px; border-radius: 4px; margin-bottom: 4px;"><span style="font-size: 0.8rem; color: #555;">⏱️ <b>{timestamp}</b> ({x}, {y})</span><br><span style="font-size: 1.0rem; color: #000;">{text}</span></div>', unsafe_allow_html=True)
            if st.button(f"▶ {timestamp} 재생 시점으로 이동", key=f"v_jump_{c_id}", use_container_width=True):
                st.session_state[f"v_start_{file_id}"] = time
                st.rerun()
        with col_ed:
            if st.button("✎", key=f"btn_ed_vid_{c_id}", help="수정"):
                st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                st.rerun()
        with col_del:
            if st.button("✕", key=f"btn_del_vid_{c_id}", help="삭제"):
                SessionStateManager.delete_video_feedback(file_id, c_id)
                save_callback()
                st.rerun()
                
        if st.session_state.get(edit_key, False):
            new_text = st.text_input("내용 수정", value=text, key=f"in_vid_{c_id}", label_visibility="collapsed")
            if st.button("✔ 저장", key=f"save_vid_{c_id}"):
                SessionStateManager.update_video_feedback(file_id, c_id, new_text)
                st.session_state[edit_key] = False
                save_callback()
                st.rerun()
        

class SessionStateManager:
    """Streamlit 세션 상태 초기화 및 관리를 도와주는 유틸리티"""
    
    @staticmethod
    def init_image_state(file_id: str):
        if "canvas_data" not in st.session_state:
            st.session_state.canvas_data = {}
        if "current_click" not in st.session_state:
            st.session_state.current_click = {}
            
        if file_id not in st.session_state.canvas_data:
            st.session_state.canvas_data[file_id] = []
            
    @staticmethod
    def init_video_state(file_id: str):
        if "video_data" not in st.session_state:
            st.session_state.video_data = {}
        if "v_current_click" not in st.session_state:
            st.session_state.v_current_click = {}
            
        if file_id not in st.session_state.video_data:
            st.session_state.video_data[file_id] = []

    @staticmethod
    def add_image_feedback(file_id: str, color: str, color_name: str, x: int, y: int, text: str):
        st.session_state.canvas_data[file_id].append({
            "id": str(uuid.uuid4())[:8],
            "color": color, 
            "color_name": color_name,
            "text": text, 
            "x": x, 
            "y": y
        })
        st.session_state.current_click[file_id] = None

    @staticmethod
    def update_image_feedback(file_id: str, c_id: str, new_text: str):
        for item in st.session_state.canvas_data.get(file_id, []):
            if item.get("id") == c_id:
                item["text"] = new_text
                break

    @staticmethod
    def delete_image_feedback(file_id: str, c_id: str):
        st.session_state.canvas_data[file_id] = [item for item in st.session_state.canvas_data.get(file_id, []) if item.get("id") != c_id]

    @staticmethod
    def add_video_feedback(file_id: str, color: str, color_name: str, time: int, x: int, y: int, text: str):
        st.session_state.video_data[file_id].append({
            "id": str(uuid.uuid4())[:8],
            "color": color,
            "color_name": color_name,
            "time": time,
            "text": text,
            "x": x,
            "y": y
        })
        # 시간 순으로 코멘트 정렬
        st.session_state.video_data[file_id] = sorted(st.session_state.video_data[file_id], key=lambda item: item['time'])
        st.session_state.v_current_click[file_id] = None

    @staticmethod
    def update_video_feedback(file_id: str, c_id: str, new_text: str):
        for item in st.session_state.video_data.get(file_id, []):
            if item.get("id") == c_id:
                item["text"] = new_text
                break

    @staticmethod
    def delete_video_feedback(file_id: str, c_id: str):
        st.session_state.video_data[file_id] = [item for item in st.session_state.video_data.get(file_id, []) if item.get("id") != c_id]

class ProjectManager:
    """프로젝트 파일 및 상태 저장을 관리하는 유틸리티"""
    BASE_DIR = os.path.join(os.path.dirname(__file__), "projects")

    @classmethod
    def _ensure_dir(cls):
        if not os.path.exists(cls.BASE_DIR):
            os.makedirs(cls.BASE_DIR)

    @classmethod
    def list_projects(cls) -> list:
        cls._ensure_dir()
        projects = []
        for d in os.listdir(cls.BASE_DIR):
            proj_dir = os.path.join(cls.BASE_DIR, d)
            state_file = os.path.join(proj_dir, "state.json")
            if os.path.isdir(proj_dir) and os.path.exists(state_file):
                with open(state_file, 'r', encoding='utf-8') as f:
                    try:
                        state = json.load(f)
                        projects.append({
                            "id": d,
                            "name": state.get("name", d),
                            "created_at": state.get("created_at", "")
                        })
                    except:
                        pass
        return sorted(projects, key=lambda x: x["created_at"], reverse=True)

    @classmethod
    def create_project(cls, name: str) -> str:
        cls._ensure_dir()
        pid = f"proj_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        proj_dir = os.path.join(cls.BASE_DIR, pid)
        os.makedirs(proj_dir)
        os.makedirs(os.path.join(proj_dir, "images"))
        os.makedirs(os.path.join(proj_dir, "videos"))
        
        initial_state = {
            "name": name,
            "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "canvas_data": {},
            "video_data": {},
            "files": {
                "images": [],
                "videos": []
            }
        }
        cls.save_state(pid, initial_state)
        return pid

    @classmethod
    def load_state(cls, pid: str) -> dict:
        state_file = os.path.join(cls.BASE_DIR, pid, "state.json")
        if os.path.exists(state_file):
            with open(state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    @classmethod
    def save_state(cls, pid: str, state: dict):
        state_file = os.path.join(cls.BASE_DIR, pid, "state.json")
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    @classmethod
    def rename_project(cls, pid: str, new_name: str):
        state = cls.load_state(pid)
        if state:
            state["name"] = new_name
            cls.save_state(pid, state)

    @classmethod
    def delete_project(cls, pid: str):
        proj_dir = os.path.join(cls.BASE_DIR, pid)
        if os.path.exists(proj_dir):
            shutil.rmtree(proj_dir)

    @classmethod
    def save_uploaded_file(cls, pid: str, file_obj, file_type: str) -> dict:
        """file_type: 'images' or 'videos'. Returns dict with path info."""
        folder = os.path.join(cls.BASE_DIR, pid, file_type)
        if not os.path.exists(folder):
            os.makedirs(folder)
            
        file_path = os.path.join(folder, file_obj.name)
        # Avoid overwriting with same name by adding suffix if exists
        base, ext = os.path.splitext(file_obj.name)
        counter = 1
        while os.path.exists(file_path):
            file_path = os.path.join(folder, f"{base}_{counter}{ext}")
            counter += 1
            
        file_obj.seek(0)
        with open(file_path, "wb") as f:
            f.write(file_obj.read())
            
        return {
            "name": os.path.basename(file_path),
            "path": file_path
        }
