import streamlit as st
from PIL import Image
import io
import os
import datetime
from streamlit_autorefresh import st_autorefresh
from feedbackutill import FeedbackConfig, ImageFeedbackUtils, VideoFeedbackUtils, SessionStateManager, ProjectManager

def resize_image(img: Image.Image, max_width: int) -> Image.Image:
    if img.width > max_width:
        ratio = max_width / float(img.width)
        return img.resize((max_width, int(img.height * ratio)), Image.Resampling.BILINEAR)
    return img

@st.cache_data(show_spinner=False)
def load_and_resize_image(img_path: str, max_width: int = 700) -> Image.Image:
    base_img = Image.open(img_path).convert("RGB")
    return resize_image(base_img, max_width)

def seconds_to_time(secs: int) -> datetime.time:
    secs = int(secs)
    hours = secs // 3600
    minutes = (secs % 3600) // 60
    seconds = secs % 60
    hours = min(hours, 23)
    return datetime.time(hours, minutes, seconds)

def time_to_seconds(t: datetime.time) -> int:
    return t.hour * 3600 + t.minute * 60 + t.second

st.set_page_config(page_title="멀티미디어 디자인 리뷰 룸 (협업/공유 버전)", layout="wide")

# 사이드바: 작업 히스토리 및 새 프로젝트
with st.sidebar:
    st.header("📂 작업 히스토리")
    
    # 새 프로젝트 생성
    with st.expander("✨ 새 프로젝트 만들기", expanded=False):
        new_proj_name = st.text_input("프로젝트 이름")
        if st.button("생성 및 시작", use_container_width=True):
            if new_proj_name.strip():
                new_pid = ProjectManager.create_project(new_proj_name.strip())
                st.query_params["project"] = new_pid
                # Clear uploaders when starting new project
                if "img_uploader_key" in st.session_state:
                    st.session_state.img_uploader_key += 1
                if "vid_uploader_key" in st.session_state:
                    st.session_state.vid_uploader_key += 1
                st.rerun()
            else:
                st.warning("이름을 입력하세요.")
                
    st.divider()
    
    # 기존 프로젝트 목록 (히스토리)
    projects = ProjectManager.list_projects()
    if not projects:
        st.info("저장된 작업 히스토리가 없습니다.")
    else:
        for p in projects:
            with st.expander(f"{p['name']} ({p['created_at'][:10]})", expanded=(p['id'] == st.query_params.get("project"))):
                if st.button("📂 이 프로젝트 열기", key=f"open_{p['id']}", use_container_width=True):
                    st.query_params["project"] = p['id']
                    # Clear uploaders when opening project
                    if "img_uploader_key" in st.session_state:
                        st.session_state.img_uploader_key += 1
                    if "vid_uploader_key" in st.session_state:
                        st.session_state.vid_uploader_key += 1
                    st.rerun()
                
                new_name = st.text_input("이름 변경", value=p['name'], key=f"ren_in_{p['id']}")
                col_ren, col_del = st.columns(2)
                with col_ren:
                    if st.button("✔ 저장", key=f"ren_btn_{p['id']}", use_container_width=True):
                        if new_name.strip() and new_name != p['name']:
                            ProjectManager.rename_project(p['id'], new_name.strip())
                            st.rerun()
                with col_del:
                    if st.button("✕ 삭제", key=f"del_btn_{p['id']}", use_container_width=True):
                        ProjectManager.delete_project(p['id'])
                        if st.query_params.get("project") == p['id']:
                            del st.query_params["project"]
                        st.rerun()

current_pid = st.query_params.get("project")

if current_pid:
    if "last_pid" not in st.session_state:
        st.session_state.last_pid = current_pid
    elif st.session_state.last_pid != current_pid:
        st.session_state.last_pid = current_pid
        # Project changed! Increment uploader keys to reset file uploaders and clear memory
        for suffix in ["img", "vid"]:
            key_name = f"{suffix}_uploader_key"
            old_val = st.session_state.get(key_name, 0)
            old_key = f"{suffix}_uploader_{old_val}"
            if old_key in st.session_state:
                del st.session_state[old_key]
            st.session_state[key_name] = old_val + 1
        # Clear coordinates
        st.session_state.current_click = {}
        st.session_state.v_current_click = {}

if not current_pid:
    st.title("🎬 프리미엄 디자인 리뷰 룸")
    st.info("👈 화면 왼쪽 사이드바에서 **[새 프로젝트 만들기]**를 통해 시작하거나 기존 히스토리를 선택해주세요.")
    st.stop()

# Auto-refresh to get real-time updates from other users (every 3 seconds)
st_autorefresh(interval=3000, key="data_refresh")

# 디스크에서 프로젝트 상태 불러오기
state = ProjectManager.load_state(current_pid)
if not state:
    st.error("프로젝트를 찾을 수 없습니다. 삭제되었거나 잘못된 링크입니다.")
    st.stop()

# ---------------------------------------------------------
# 상태 동기화 (디스크 state.json -> 세션 상태)
# 다른 사람이 피드백을 달았을 때 새로고침되며 바로 반영되게 함
# ---------------------------------------------------------
if "canvas_data" not in st.session_state:
    st.session_state.canvas_data = {}
if "video_data" not in st.session_state:
    st.session_state.video_data = {}

st.session_state.canvas_data = state.get("canvas_data", {})
st.session_state.video_data = state.get("video_data", {})

if "current_click" not in st.session_state:
    st.session_state.current_click = {}
if "v_current_click" not in st.session_state:
    st.session_state.v_current_click = {}

# 헤더 및 공유 링크 안내
col_title, col_share = st.columns([6, 4])
with col_title:
    st.title(f"🎬 {state.get('name', '프로젝트')} 리뷰 룸")
with col_share:
    st.markdown("<br>", unsafe_allow_html=True)
    st.info("🔗 주소창의 URL을 복사하여 공유하면 **실시간 동기화 리뷰**가 가능합니다.")

tab_img, tab_vid, tab_card = st.tabs(["🖼️ 이미지 피드백", "🎥 영상 피드백", "⭐ 후기 이미지 생성기"])

# ==========================================
# [TAB 1: 이미지 피드백]
# ==========================================
with tab_img:
    st.subheader("이미지 리뷰 섹션")
    
    # 1. 이미 업로드되어 저장된 이미지 렌더링
    saved_images = state.get("files", {}).get("images", [])
    for img_info in reversed(saved_images):
        f_id = f"img_{img_info['name']}"
        SessionStateManager.init_image_state(f_id)
        
        st.write("---")
        # 업로드 일시 표시 (상단 아주 작게 회색 글씨, 24시간 형식)
        uploaded_at = img_info.get("uploaded_at")
        if not uploaded_at and os.path.exists(img_info['path']):
            try:
                mtime = os.path.getmtime(img_info['path'])
                dt = datetime.datetime.fromtimestamp(mtime)
                uploaded_at = f"{dt.year}년 {dt.month:02d}월 {dt.day:02d}일 {dt.hour:02d}시 {dt.minute:02d}분"
            except Exception:
                pass
                
        if uploaded_at:
            st.markdown(f"<div style='color: #888888; font-size: 11px; margin-bottom: -10px;'>🕒 업로드 일시: {uploaded_at}</div>", unsafe_allow_html=True)
            
        col_title, col_delete = st.columns([8, 2])
        with col_title:
            st.markdown(f"#### 🖼️ {img_info['name']}")
        with col_delete:
            if st.button("🗑️ 이미지 삭제", key=f"del_img_file_{f_id}", use_container_width=True):
                if os.path.exists(img_info['path']):
                    try:
                        os.remove(img_info['path'])
                    except Exception:
                        pass
                state["files"]["images"] = [x for x in state["files"]["images"] if x['name'] != img_info['name']]
                if f_id in state.get("canvas_data", {}):
                    del state["canvas_data"][f_id]
                ProjectManager.save_state(current_pid, state)
                st.rerun()
        
        col_img, col_chat = st.columns([7, 3])
        
        with col_img:
            sel_color = st.radio("핀 색상", list(FeedbackConfig.COLOR_MAP.keys()), key=f"r_{f_id}", horizontal=True)
            
            # Sync coordinate from widget state before rendering to optimize latency (no double rerun)
            coords_key = f"coords_{f_id}"
            coords = st.session_state.get(coords_key)
            if coords and coords != st.session_state.current_click.get(f_id):
                st.session_state.current_click[f_id] = coords
                
            active_click = st.session_state.current_click.get(f_id)
            
            # 디스크에서 원본 이미지 불러오기 및 리사이징 (캐시 활용 최적화)
            base_img = load_and_resize_image(img_info['path'], max_width=700)
            
            img_with_pins = ImageFeedbackUtils.draw_pins(
                base_img=base_img,
                comments=st.session_state.canvas_data.get(f_id, []),
                active_click=active_click,
                active_color=FeedbackConfig.COLOR_MAP[sel_color]
            )
            
            from streamlit_image_coordinates import streamlit_image_coordinates
            # Set explicit width to prevent browser scaling offset!
            streamlit_image_coordinates(img_with_pins, width=base_img.width, key=coords_key)

        with col_chat:
            st.write("💬 **이미지 피드백 챗**")
            f_back = st.chat_input("의견 입력 후 엔터", key=f"chat_{f_id}")
            
            if f_back:
                if active_click:
                    # 세션에 코멘트 추가 후 즉시 JSON 파일로 덮어쓰기 (실시간 공유 목적)
                    SessionStateManager.add_image_feedback(f_id, FeedbackConfig.COLOR_MAP[sel_color], sel_color, active_click["x"], active_click["y"], f_back)
                    state["canvas_data"] = st.session_state.canvas_data
                    ProjectManager.save_state(current_pid, state)
                    # Clear coordinates from session state
                    if coords_key in st.session_state:
                        st.session_state[coords_key] = None
                    st.rerun()
                else:
                    st.warning("이미지 위를 먼저 클릭하세요!")
            
            for comm in st.session_state.canvas_data.get(f_id, []):
                ImageFeedbackUtils.render_feedback_card(f_id, comm, lambda: ProjectManager.save_state(current_pid, state))
            
            # HTML 내보내기 버튼 추가
            image_comments = st.session_state.canvas_data.get(f_id, [])
            if image_comments:
                st.write("---")
                from html_exporter import export_image_project_to_html
                html_code = export_image_project_to_html(state.get("name", "프로젝트"), img_info['name'], img_info['path'], image_comments)
                st.download_button(
                    label="📥 대화형 HTML로 내보내기 (공유용)",
                    data=html_code,
                    file_name=f"{state.get('name', '프로젝트')}_{img_info['name']}_feedback.html",
                    mime="text/html",
                    use_container_width=True,
                    key=f"dl_html_{f_id}"
                )
 
    # 2. 이미지 추가 업로드
    st.write("---")
    if "img_uploader_key" not in st.session_state:
        st.session_state.img_uploader_key = 0
        
    new_img_files = st.file_uploader("추가할 이미지 업로드", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key=f"img_uploader_{st.session_state.img_uploader_key}")
    if new_img_files:
        if st.button("새 이미지 저장 및 프로젝트에 추가", use_container_width=True):
            from datetime import datetime
            now = datetime.now()
            uploaded_time = f"{now.year}년 {now.month:02d}월 {now.day:02d}일 {now.hour:02d}시 {now.minute:02d}분"
            for file in new_img_files:
                file_info = ProjectManager.save_uploaded_file(current_pid, file, "images")
                file_info["uploaded_at"] = uploaded_time
                state["files"]["images"].append(file_info)
            ProjectManager.save_state(current_pid, state)
            
            # Clear file uploader memory explicitly
            old_key = f"img_uploader_{st.session_state.img_uploader_key}"
            if old_key in st.session_state:
                del st.session_state[old_key]
            st.session_state.img_uploader_key += 1
            st.rerun()

# ==========================================
# [TAB 2: 영상 피드백]
# ==========================================
with tab_vid:
    st.subheader("영상 리뷰 섹션")
    
    saved_videos = state.get("files", {}).get("videos", [])
    for vid_info in reversed(saved_videos):
        v_id = f"vid_{vid_info['name']}"
        SessionStateManager.init_video_state(v_id)
            
        st.write("---")
        # 업로드 일시 표시 (상단 아주 작게 회색 글씨, 24시간 형식)
        uploaded_at = vid_info.get("uploaded_at")
        if not uploaded_at and os.path.exists(vid_info['path']):
            try:
                mtime = os.path.getmtime(vid_info['path'])
                dt = datetime.datetime.fromtimestamp(mtime)
                uploaded_at = f"{dt.year}년 {dt.month:02d}월 {dt.day:02d}일 {dt.hour:02d}시 {dt.minute:02d}분"
            except Exception:
                pass
                
        if uploaded_at:
            st.markdown(f"<div style='color: #888888; font-size: 11px; margin-bottom: -10px;'>🕒 업로드 일시: {uploaded_at}</div>", unsafe_allow_html=True)
            
        col_title, col_delete = st.columns([8, 2])
        with col_title:
            st.markdown(f"#### 🎥 {vid_info['name']}")
        with col_delete:
            if st.button("🗑️ 영상 삭제", key=f"del_vid_file_{v_id}", use_container_width=True):
                if os.path.exists(vid_info['path']):
                    try:
                        os.remove(vid_info['path'])
                    except Exception:
                        pass
                state["files"]["videos"] = [x for x in state["files"]["videos"] if x['name'] != vid_info['name']]
                if v_id in state.get("video_data", {}):
                    del state["video_data"][v_id]
                ProjectManager.save_state(current_pid, state)
                st.rerun()
        
        col_vid, col_vchat = st.columns([5, 5])
        
        with col_vid:
            # 비디오 파일의 실제 재생 길이(초)를 구합니다.
            duration = VideoFeedbackUtils.get_video_duration(vid_info['path'])
            # 디스크 경로를 직접 넘겨 스트리밍 렌더링 (사운드 및 로딩 성능 최적화)
            v_start_time = min(st.session_state.get(f"v_start_{v_id}", 0), duration)
            st.video(vid_info['path'], start_time=v_start_time)
            
            st.markdown("#### 🛠️ 타임라인 핀 지정 도구")
            
            # 구간 선택 여부 체크박스
            is_range_key = f"v_range_check_{v_id}"
            is_range = st.checkbox("구간 선택 (시작 ~ 종료 시점 피드백)", value=False, key=is_range_key)
            
            # Safe check and conversion of slider session state
            slider_key = f"v_slider_{v_id}"
            fmt = "mm:ss" if duration < 3600 else "HH:mm:ss"
            
            if is_range:
                # Range selection mode
                default_range = (seconds_to_time(v_start_time), seconds_to_time(min(v_start_time + 10, duration)))
                current_slider_val = st.session_state.get(slider_key, default_range)
                if not isinstance(current_slider_val, tuple) or len(current_slider_val) != 2:
                    current_slider_val = default_range
                    st.session_state[slider_key] = current_slider_val
                
                # Ensure the bounds are correct datetime.time types
                start_t, end_t = current_slider_val
                if isinstance(start_t, (int, float)):
                    start_t = seconds_to_time(start_t)
                if isinstance(end_t, (int, float)):
                    end_t = seconds_to_time(end_t)
                current_slider_val = (start_t, end_t)
                st.session_state[slider_key] = current_slider_val
                
                target_time_tuple = st.slider(
                    "타임라인 슬라이더",
                    min_value=seconds_to_time(0),
                    max_value=seconds_to_time(duration),
                    value=current_slider_val,
                    key=slider_key,
                    step=datetime.timedelta(seconds=1),
                    format=fmt,
                    label_visibility="collapsed"
                )
                start_seconds = time_to_seconds(target_time_tuple[0])
                end_seconds = time_to_seconds(target_time_tuple[1])
                target_seconds = start_seconds  # Draw pins and preview at the start point
            else:
                # Single point selection mode
                current_slider_val = st.session_state.get(slider_key, seconds_to_time(v_start_time))
                if isinstance(current_slider_val, tuple):
                    current_slider_val = current_slider_val[0]
                if isinstance(current_slider_val, (int, float)):
                    current_slider_val = seconds_to_time(current_slider_val)
                st.session_state[slider_key] = current_slider_val
                
                target_time = st.slider(
                    "타임라인 슬라이더",
                    min_value=seconds_to_time(0),
                    max_value=seconds_to_time(duration),
                    value=current_slider_val,
                    key=slider_key,
                    step=datetime.timedelta(seconds=1),
                    format=fmt,
                    label_visibility="collapsed"
                )
                target_seconds = time_to_seconds(target_time)
                start_seconds = target_seconds
                end_seconds = target_seconds
                
            v_min = target_seconds // 60
            v_sec = target_seconds % 60
            
            if is_range:
                start_time_str = f"{start_seconds // 60:02d}:{start_seconds % 60:02d}"
                end_time_str = f"{end_seconds // 60:02d}:{end_seconds % 60:02d}"
                st.markdown(f"**⏳ 타임라인 위치 선택 ({start_time_str} ~ {end_time_str} / {duration // 60:02d}:{duration % 60:02d})**")
            else:
                current_time_str = f"{target_seconds // 60:02d}:{target_seconds % 60:02d}"
                total_time_str = f"{duration // 60:02d}:{duration % 60:02d}"
                st.markdown(f"**⏳ 타임라인 위치 선택 ({current_time_str} / {total_time_str})**")

        with col_vchat:
            st.write("🎨 **핀 색상 선택**")
            v_sel_color = st.radio(
                "핀 색상 선택",
                list(FeedbackConfig.COLOR_MAP.keys()),
                key=f"v_radio_{v_id}",
                horizontal=True,
                label_visibility="collapsed"
            )
            st.write("📸 **선택된 재생시점 스냅샷 (클릭하여 핀 꼽기)**")
            
            # Sync coordinate from widget state before rendering to optimize latency (no double rerun)
            v_coords_key = f"v_coords_{v_id}"
            v_coords = st.session_state.get(v_coords_key)
            if v_coords and v_coords != st.session_state.v_current_click.get(v_id):
                st.session_state.v_current_click[v_id] = v_coords
                
            v_active = st.session_state.v_current_click.get(v_id)
            
            v_image = VideoFeedbackUtils.extract_frame_from_path(vid_info['path'], target_seconds)
            if v_image:
                # 리사이징이 extract_frame_from_path 내부에서 이루어지므로 bilinear 호출 최적화 완료
                v_image_with_pins = VideoFeedbackUtils.draw_pins_on_frame(
                    base_img=v_image,
                    comments=st.session_state.video_data.get(v_id, []),
                    target_seconds=target_seconds,
                    active_click=v_active,
                    active_color=FeedbackConfig.COLOR_MAP[v_sel_color]
                )
                
                if is_range:
                    start_time_str = f"{start_seconds // 60:02d}:{start_seconds % 60:02d}"
                    end_time_str = f"{end_seconds // 60:02d}:{end_seconds % 60:02d}"
                    st.caption(f"🎯 **현재 타임라인 구간 ({start_time_str} ~ {end_time_str})** - 아래 화면을 클릭하여 위치를 지정하세요.")
                else:
                    st.caption(f"🎯 **현재 타임라인 ({v_min:02d}:{v_sec:02d})** - 아래 화면을 클릭하여 위치를 지정하세요.")
                
                from streamlit_image_coordinates import streamlit_image_coordinates
                # Set explicit width to prevent browser scaling offset!
                streamlit_image_coordinates(v_image_with_pins, width=v_image.width, key=v_coords_key)
            else:
                st.warning("⚠️ 프레임을 읽을 수 없습니다.")

            st.write("---")
            st.write("💬 **영상 타임라인 챗**")
            v_feedback = st.chat_input("타임라인 피드백을 적고 엔터", key=f"vchat_{v_id}")
            
            if v_feedback:
                if v_active:
                    SessionStateManager.add_video_feedback(
                        v_id, 
                        FeedbackConfig.COLOR_MAP[v_sel_color], 
                        v_sel_color, 
                        start_seconds, 
                        v_active["x"], 
                        v_active["y"], 
                        v_feedback,
                        end_time=end_seconds
                    )
                    state["video_data"] = st.session_state.video_data
                    ProjectManager.save_state(current_pid, state)
                    # Clear coordinates state
                    if v_coords_key in st.session_state:
                        st.session_state[v_coords_key] = None
                    st.rerun()
                else:
                    st.warning("⚠️ 위의 스냅샷 화면에서 위치를 먼저 클릭해 주세요!")
            
            v_comments = st.session_state.video_data.get(v_id, [])
            if not v_comments:
                st.info("좌측에서 분/초 지정 후, 위 스냅샷을 클릭해 피드백을 남겨보세요.")
            else:
                for vc in v_comments:
                    VideoFeedbackUtils.render_feedback_card(v_id, vc, lambda: ProjectManager.save_state(current_pid, state))
                
                st.write("---")
                from html_exporter import export_video_project_to_html
                v_html_code = export_video_project_to_html(state.get("name", "프로젝트"), vid_info['name'], v_comments)
                st.download_button(
                    label="📥 대화형 HTML로 내보내기 (공유용)",
                    data=v_html_code,
                    file_name=f"{state.get('name', '프로젝트')}_{vid_info['name']}_feedback.html",
                    mime="text/html",
                    use_container_width=True,
                    key=f"dl_html_{v_id}"
                )

    # 2. 영상 추가 업로드
    st.write("---")
    if "vid_uploader_key" not in st.session_state:
        st.session_state.vid_uploader_key = 0
        
    new_vid_files = st.file_uploader("추가할 영상 업로드", type=["mp4", "mov", "avi"], accept_multiple_files=True, key=f"vid_uploader_{st.session_state.vid_uploader_key}")
    if new_vid_files:
        if st.button("새 영상 저장 및 프로젝트에 추가", use_container_width=True):
            from datetime import datetime
            now = datetime.now()
            uploaded_time = f"{now.year}년 {now.month:02d}월 {now.day:02d}일 {now.hour:02d}시 {now.minute:02d}분"
            for file in new_vid_files:
                file_info = ProjectManager.save_uploaded_file(current_pid, file, "videos")
                file_info["uploaded_at"] = uploaded_time
                state["files"]["videos"].append(file_info)
            ProjectManager.save_state(current_pid, state)
            
            # Clear file uploader memory explicitly
            old_key = f"vid_uploader_{st.session_state.vid_uploader_key}"
            if old_key in st.session_state:
                del st.session_state[old_key]
            st.session_state.vid_uploader_key += 1
            st.rerun()

# ==========================================
# [TAB 3: 후기 이미지 생성기]
# ==========================================
with tab_card:
    st.subheader("⭐ 학생 후기 이미지 생성기")
    st.markdown("""
    학생들의 생생한 후기를 SNS나 마케팅에 즉시 활용할 수 있는 **카드 형태의 고화질 이미지**로 변환하는 도구입니다.
    
    * **팁**: 아래의 생성기에서 디자인하고 **[고화질 이미지 다운로드]** 버튼을 클릭하세요!
    * **브라우저 다운로드 주의**: 일부 브라우저 보안 정책에 따라 내장 화면(iframe) 내부에서 다운로드가 제한될 수 있습니다. 
      만약 다운로드 버튼이 작동하지 않는다면 아래의 **[독립 실행용 HTML 파일 다운로드]** 버튼을 통해 파일을 저장한 후, 
      그 파일을 더블 클릭하여 웹 브라우저에서 직접 여시면 다운로드 기능이 100% 완벽히 작동합니다.
    """)
    
    # 단독 파일 열기 버튼
    html_file_path = os.path.join(os.path.dirname(__file__), "review_generator.html")
    if os.path.exists(html_file_path):
        with open(html_file_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # HTML 다운로드 버튼 제공
        col_down, _ = st.columns([4, 6])
        with col_down:
            st.download_button(
                label="📁 독립 실행용 HTML 파일 다운로드 및 실행",
                data=html_content,
                file_name="review_generator.html",
                mime="text/html",
                use_container_width=True
            )
            
        st.write("---")
        
        # iframe 임베딩
        import streamlit.components.v1 as components
        components.html(html_content, height=950, scrolling=True)
    else:
        st.error("후기 생성기 파일(review_generator.html)을 찾을 수 없습니다.")
