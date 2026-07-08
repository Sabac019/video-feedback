import os
import io
import base64
from PIL import Image
from feedbackutill import ImageFeedbackUtils

# ==============================================================================
# HTML 공통 템플릿 CSS/JS 스타일 정의 (세련된 다크 블루-그레이 디자인)
# ==============================================================================
HTML_STYLE = """
<style>
    :root {
        --color-bg: #1a2633;
        --color-panel: #213143;
        --color-header: #1e2f41;
        --color-text-primary: #f1f5f9;
        --color-text-muted: #94a3b8;
        --color-accent: #10b981;
        --color-accent-hover: #059669;
        --color-tag-time: #10b981;
        --color-tag-general: #f59e0b;
        --color-checked-bg: #182431;
        --color-checked-text: #64748b;
        --color-border: #334155;
    }

    * {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
    }

    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Malgun Gothic", sans-serif;
        background-color: var(--color-bg);
        color: var(--color-text-primary);
        line-height: 1.5;
        padding-bottom: 50px;
    }

    /* 최상단 헤더 */
    header {
        background-color: var(--color-header);
        padding: 15px 30px;
        border-bottom: 1px solid var(--color-border);
    }

    header h1 {
        font-size: 20px;
        font-weight: 700;
        margin-bottom: 4px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    header p {
        font-size: 13px;
        color: var(--color-text-muted);
    }

    /* 메인 콘텐츠 컨테이너 */
    .container {
        display: flex;
        flex-wrap: wrap;
        max-width: 1300px;
        margin: 20px auto;
        padding: 0 15px;
        gap: 20px;
    }

    .panel-left, .panel-right {
        flex: 1;
        min-width: 400px;
        background-color: var(--color-panel);
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }

    .panel-title {
        font-size: 15px;
        font-weight: 700;
        margin-bottom: 15px;
        border-bottom: 1px solid var(--color-border);
        padding-bottom: 8px;
    }

    /* 미디어 표시 영역 */
    .media-container {
        display: flex;
        justify-content: center;
        align-items: center;
        background-color: #111b24;
        border-radius: 6px;
        padding: 10px;
        min-height: 350px;
        position: relative;
    }

    .media-container img {
        max-width: 100%;
        height: auto;
        border-radius: 4px;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3);
    }

    video {
        width: 100%;
        max-height: 500px;
        border-radius: 4px;
        background: #000;
    }

    /* 비디오 로더 카드 */
    .video-loader-card {
        text-align: center;
        padding: 40px 20px;
        width: 100%;
    }

    .video-loader-card h3 {
        margin-bottom: 10px;
        font-size: 16px;
    }

    .video-loader-card p {
        font-size: 13px;
        color: var(--color-text-muted);
        margin-bottom: 20px;
    }

    .file-input-btn {
        display: inline-block;
        padding: 10px 20px;
        background-color: var(--color-accent);
        color: white;
        font-weight: bold;
        border-radius: 6px;
        cursor: pointer;
        transition: background 0.2s;
    }

    .file-input-btn:hover {
        background-color: var(--color-accent-hover);
    }

    #video-file-input {
        display: none;
    }

    /* 피드백 체크리스트 아이템 */
    .feedback-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
        max-height: 500px;
        overflow-y: auto;
        padding-right: 5px;
    }

    /* 스크롤바 커스텀 */
    .feedback-list::-webkit-scrollbar {
        width: 6px;
    }
    .feedback-list::-webkit-scrollbar-track {
        background: var(--color-bg);
        border-radius: 4px;
    }
    .feedback-list::-webkit-scrollbar-thumb {
        background: var(--color-border);
        border-radius: 4px;
    }

    .feedback-row {
        display: flex;
        align-items: center;
        background-color: var(--color-panel);
        border: 1px solid var(--color-border);
        border-radius: 6px;
        padding: 12px 15px;
        cursor: pointer;
        transition: background 0.2s, transform 0.1s;
        gap: 12px;
    }

    .feedback-row:hover {
        background-color: #2b3d53;
        transform: translateY(-1px);
    }

    .feedback-checkbox {
        font-size: 18px;
        cursor: pointer;
        user-select: none;
        color: #8b5cf6;
    }

    .tag {
        font-size: 11px;
        font-weight: bold;
        padding: 2px 6px;
        border-radius: 4px;
        white-space: nowrap;
    }

    .tag-time {
        color: var(--color-tag-time);
        background-color: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.2);
    }

    .tag-general {
        color: var(--color-tag-general);
        background-color: rgba(245, 158, 11, 0.1);
        border: 1px solid rgba(245, 158, 11, 0.2);
    }

    .feedback-text {
        font-size: 13px;
        flex: 1;
        word-break: break-all;
    }

    /* 완료된 상태 클래스 */
    .feedback-row.checked {
        background-color: var(--color-checked-bg) !important;
        opacity: 0.6;
    }

    .feedback-row.checked .feedback-checkbox {
        color: var(--color-accent);
    }

    .feedback-row.checked .feedback-text {
        text-decoration: line-through;
        color: var(--color-checked-text);
    }

    .feedback-row.checked .tag {
        opacity: 0.5;
        text-decoration: line-through;
    }
</style>
"""

# ==============================================================================
# HTML 파일 내보내기용 정적 마크업 템플릿 정의 (f-string이 아님)
# ==============================================================================
IMAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>[공유] {{PROJECT_NAME}} - 이미지 피드백 룸</title>
    {{STYLE}}
</head>
<body>
    <header>
        <h1>🖼️ [피드백 공유] {{PROJECT_NAME}}</h1>
        <p>상대방이 이미지 위에 지정해둔 핀 정보와 피드백 상세 리스트입니다. 항목을 클릭해 완료 표시를 할 수 있습니다.</p>
    </header>

    <div class="container">
        <!-- 왼쪽: 핀이 찍힌 이미지 영역 -->
        <div class="panel-left">
            <div class="panel-title">🖼️ 피드백이 지정된 이미지 ({{IMAGE_NAME}})</div>
            <div class="media-container">
                {{IMAGE_CONTENT}}
            </div>
        </div>

        <!-- 오른쪽: 피드백 체크리스트 -->
        <div class="panel-right">
            <div class="panel-title">✅ 이미지 피드백 체크리스트 ({{COMMENT_COUNT}}개)</div>
            <div class="feedback-list">
                {{LIST_ROWS}}
            </div>
        </div>
    </div>

    <script>
        const checkedStates = {};
        
        function toggleCheck(idx) {
            const row = document.querySelectorAll('.feedback-row')[idx];
            const icon = document.getElementById('check-icon-' + idx);
            
            checkedStates[idx] = !checkedStates[idx];
            
            if (checkedStates[idx]) {
                row.classList.add('checked');
                icon.innerText = '☑';
            } else {
                row.classList.remove('checked');
                icon.innerText = '☐';
            }
        }
    </script>
</body>
</html>
"""

VIDEO_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>[공유] {{PROJECT_NAME}} - 비디오 피드백 룸</title>
    {{STYLE}}
</head>
<body>
    <header>
        <h1>🎥 [피드백 공유] {{PROJECT_NAME}}</h1>
        <p>영상의 피드백 리스트입니다. 리스트 항목을 클릭하면 해당 시간대의 구간으로 비디오가 바로 점프합니다!</p>
    </header>

    <div class="container">
        <!-- 왼쪽: 비디오 플레이어 -->
        <div class="panel-left">
            <div class="panel-title">🎥 비디오 플레이어 ({{VIDEO_NAME}})</div>
            <div class="media-container" id="player-area">
                <!-- 파일 업로드 카드 -->
                <div class="video-loader-card">
                    <h3>🎥 동영상 파일 불러오기</h3>
                    <p>본 피드백은 로컬 보안 파일입니다. 재생할 원본 비디오 파일({{VIDEO_NAME}})을 선택하세요.</p>
                    <label for="video-file-input" class="file-input-btn">📂 영상 파일 선택</label>
                    <input type="file" id="video-file-input" accept="video/*">
                </div>
                <!-- 숨겨진 비디오 태그 -->
                <video id="video-player" controls style="display: none;"></video>
            </div>
        </div>

        <!-- 오른쪽: 피드백 타임라인 리스트 -->
        <div class="panel-right">
            <div class="panel-title">✅ 타임라인 체크리스트 ({{COMMENT_COUNT}}개)</div>
            <div class="feedback-list">
                {{LIST_ROWS}}
            </div>
        </div>
    </div>

    <script>
        const checkedStates = {};
        const videoPlayer = document.getElementById('video-player');
        const videoLoader = document.querySelector('.video-loader-card');

        // 파일 입력 이벤트 감지 -> 비디오 재생에 연동
        document.getElementById('video-file-input').addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (file) {
                const fileURL = URL.createObjectURL(file);
                videoPlayer.src = fileURL;
                videoPlayer.style.display = 'block';
                videoLoader.style.display = 'none';
            }
        });

        // 특정 시간대로 비디오 이동 함수
        function jumpToTime(seconds, event) {
            if (event && (event.target.classList.contains('feedback-checkbox') || event.target.tagName === 'INPUT')) {
                return;
            }
            if (!videoPlayer.src) {
                alert("먼저 왼쪽 화면에서 동영상 파일({{VIDEO_NAME}})을 불러와 주세요!");
                return;
            }
            videoPlayer.currentTime = seconds;
            videoPlayer.play();
        }

        // 체크 상태 전환
        function toggleCheck(idx) {
            const row = document.querySelectorAll('.feedback-row')[idx];
            const icon = document.getElementById('check-icon-' + idx);
            
            checkedStates[idx] = !checkedStates[idx];
            
            if (checkedStates[idx]) {
                row.classList.add('checked');
                icon.innerText = '☑';
            } else {
                row.classList.remove('checked');
                icon.innerText = '☐';
            }
        }
    </script>
</body>
</html>
"""

# ==============================================================================
# 이미지 피드백 프로젝트 HTML 익스포트 함수
# ==============================================================================
def export_image_project_to_html(project_name: str, image_name: str, image_path: str, comments: list) -> str:
    """
    이미지 위에 그려진 핀이 포함된 PIL 이미지를 Base64 인코딩하여 HTML에 박아 넣습니다.
    로컬 브라우저에서 무설치/무서버 상태로 바로 코멘트를 보며 작업할 수 있게 합니다.
    """
    import requests
    from io import BytesIO
    image_content_html = ""
    try:
        if image_path.startswith("http"):
            response = requests.get(image_path)
            base_img = Image.open(BytesIO(response.content)).convert("RGB")
        else:
            base_img = Image.open(image_path).convert("RGB")
            
        if base_img.width > 700:
            ratio = 700 / float(base_img.width)
            base_img = base_img.resize((700, int(base_img.height * ratio)), Image.Resampling.LANCZOS)
        
        img_with_pins = ImageFeedbackUtils.draw_pins(
            base_img=base_img,
            comments=comments,
            active_click=None
        )
        
        buffer = io.BytesIO()
        img_with_pins.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        image_src = f"data:image/png;base64,{img_base64}"
        image_content_html = f"<img src='{image_src}' alt='Feedback Image'>"
    except Exception as e:
        image_content_html = f"<p style='color:red;'>이미지를 불러오는 중에 오류가 발생했습니다: {str(e)}</p>"
        
    list_rows_html = ""
    for idx, c in enumerate(comments):
        color_tag = c.get('color_name', '📌')
        list_rows_html += f"""
        <div class="feedback-row" onclick="toggleCheck({idx})">
            <span class="feedback-checkbox" id="check-icon-{idx}">☐</span>
            <span class="tag tag-general">{color_tag} 핀 ({c['x']}, {c['y']})</span>
            <span class="feedback-text">{c['text']}</span>
        </div>
        """

    # 플레이스홀더 치환 방식 사용 (f-string 중괄호 오류 우회)
    html_content = IMAGE_TEMPLATE.replace("{{PROJECT_NAME}}", project_name) \
                                 .replace("{{STYLE}}", HTML_STYLE) \
                                 .replace("{{IMAGE_NAME}}", image_name) \
                                 .replace("{{IMAGE_CONTENT}}", image_content_html) \
                                 .replace("{{COMMENT_COUNT}}", str(len(comments))) \
                                 .replace("{{LIST_ROWS}}", list_rows_html)
    return html_content

# ==============================================================================
# 비디오 피드백 프로젝트 HTML 익스포트 함수
# ==============================================================================
def export_video_project_to_html(project_name: str, video_name: str, comments: list) -> str:
    """
    영상 파일은 용량이 크므로 직접 박아 넣지 않는 대신,
    상대방이 HTML을 켜서 컴퓨터 내부의 비디오 파일을 연동하면 동작하는 반응형 HTML을 생성합니다.
    피드백을 클릭하면 영상이 정확한 타임코드로 즉각 이동합니다.
    """
    timeline_comments = []
    general_comments = []
    
    for c in comments:
        if 'time' in c:
            timeline_comments.append(c)
        else:
            general_comments.append(c)
            
    timeline_comments.sort(key=lambda x: x.get('time', 0))
    sorted_comments = timeline_comments + general_comments

    list_rows_html = ""
    for idx, c in enumerate(sorted_comments):
        is_timeline = 'time' in c
        time_sec = c.get('time', 0)
        
        mins = time_sec // 60
        secs = time_sec % 60
        timestamp = f"{mins:02d}:{secs:02d}"
        
        if is_timeline:
            tag_class = "tag-time"
            tag_text = f"⏱️ {timestamp}"
            click_action = f"jumpToTime({time_sec}, event)"
        else:
            tag_class = "tag-general"
            tag_text = "[일반]"
            click_action = ""
            
        list_rows_html += f"""
        <div class="feedback-row" onclick="toggleCheck({idx}); {click_action}">
            <span class="feedback-checkbox" id="check-icon-{idx}">☐</span>
            <span class="tag {tag_class}">{tag_text}</span>
            <span class="feedback-text">{c['text']}</span>
        </div>
        """

    # 플레이스홀더 치환 방식 사용 (f-string 중괄호 오류 우회)
    html_content = VIDEO_TEMPLATE.replace("{{PROJECT_NAME}}", project_name) \
                                 .replace("{{STYLE}}", HTML_STYLE) \
                                 .replace("{{VIDEO_NAME}}", video_name) \
                                 .replace("{{COMMENT_COUNT}}", str(len(sorted_comments))) \
                                 .replace("{{LIST_ROWS}}", list_rows_html)
    return html_content
