import streamlit as st
import numpy as np
import plotly.graph_objects as go

# 1. 페이지 셋업
st.set_page_config(page_title="Disease X Simulator", layout="wide")
st.markdown("<style>.block-container { padding-top: 1rem; padding-bottom: 0rem; }</style>", unsafe_allow_html=True)

# 2. [사이드바] 통제실
with st.sidebar:
    st.header("🦠 방역 통제 콘솔")
    
    disease_type = st.selectbox("1. 병원체 선택", ["코로나19 (오미크론)", "흑사병", "신종 감염병 (Disease X)"])
    if disease_type == "신종 감염병 (Disease X)":
        R0 = st.slider("R0 (전파력)", 1.0, 20.0, 5.0, 0.1)
        fatality_rate = st.slider("치명률 (%)", 0.0, 50.0, 2.0, 0.1) / 100
        recovery_days = st.slider("평균 회복 소요일", 3, 30, 10)
    elif disease_type == "코로나19 (오미크론)":
        R0, fatality_rate, recovery_days = 10.0, 0.005, 7
    else: 
        R0, fatality_rate, recovery_days = 3.0, 0.3, 10
    
    st.divider()
    st.subheader("2. 방역 및 백신 정책")
    mask_on = st.checkbox("😷 마스크 의무화")
    gathering_ban = st.checkbox("🚫 모임 금지")
    lockdown = st.toggle("🔒 도시 간 이동 전면 봉쇄")
    
    st.divider()
    st.subheader("⚙️ 시뮬레이션 설정")
    # 속도 조절 슬라이더 (숫자가 작을수록 빠름: 1프레임당 밀리초 단위)
    anim_speed = st.select_slider("재생 속도", options=["느림", "보통", "빠름"], value="보통")
    speed_dict = {"느림": 500, "보통": 200, "빠름": 50}
    
    st.divider()
    run_button = st.button("▶️ 시뮬레이션 데이터 생성", use_container_width=True, type="primary")

# 3. [데이터 셋업] 
cities = ['서울', '대전', '대구', '광주', '부산']
lats = [37.5665, 36.3504, 35.8714, 35.1595, 35.1796]
lons = [126.9780, 127.3845, 128.6014, 126.8526, 129.0756]
pops = np.array([100000, 15000, 24000, 15000, 34000])

st.title("전염병 확산 시뮬레이터")

if run_button:
    # 4. [백엔드 선연산 로직] 60일치 데이터를 순식간에 미리 계산
    beta = R0 / recovery_days
    if mask_on: beta *= 0.22
    if gathering_ban: beta *= 0.58
    gamma = (1 - fatality_rate) / recovery_days
    mu = fatality_rate / recovery_days
    
    I_current = np.array([10.0, 0.0, 0.0, 0.0, 0.0])
    S_current = pops - I_current
    R_current = np.zeros(5)
    D_current = np.zeros(5)
    
    history_S, history_I, history_R, history_D = [], [], [], []
    map_frames = [] # 애니메이션 프레임을 담을 리스트
    
    for day in range(61):
        # 1) 수학 연산
        new_infections = beta * S_current * I_current / pops
        new_recoveries = gamma * I_current
        new_deaths = mu * I_current
        
        travel_rate = 0.01 if not lockdown else 0.0001 
        travelers = I_current[0] * travel_rate
        for i in range(1, 5):
            new_infections[i] += travelers / 4
            
        S_current = S_current - new_infections
        I_current = I_current + new_infections - new_recoveries - new_deaths
        R_current = R_current + new_recoveries
        D_current = D_current + new_deaths
        
        # 2) 전체 통계 기록 (그래프용)
        history_S.append(np.sum(S_current))
        history_I.append(np.sum(I_current))
        history_R.append(np.sum(R_current))
        history_D.append(np.sum(D_current))
        
        # 3) 🌟 [핵심] 1일차 단위의 지도 프레임 생성 후 저장
        frame = go.Frame(
            data=[go.Scattermapbox(
                lat=lats, lon=lons, mode='markers+text',
                marker=dict(size=I_current / 500 + 5, color='red', opacity=0.7),
                text=[f"{city}<br>감염: {int(I_current[idx])}" for idx, city in enumerate(cities)],
                textposition="bottom right"
            )],
            name=str(day) # 프레임 이름 (타임라인용)
        )
        map_frames.append(frame)

    # 5. [메인 화면 출력]
    # 요약 지표 (60일 시뮬레이션 종료 시점의 최종 결과)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("최대 동시 감염자 (Peak)", f"{int(max(history_I)):,} 명")
    col2.metric("최종 누적 사망자", f"{int(history_D[-1]):,} 명")
    if max(history_I) > 30000:
        col3.metric("의료 체계 상태", "🚨 붕괴 위기", delta_color="inverse")
    else:
        col3.metric("의료 체계 상태", "✅ 통제 성공")
    col4.metric("적용된 감염률(β)", f"{beta:.3f}")
    st.divider()

    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.subheader("📍 애니메이션 확산 지도 (Play 버튼 클릭)")
        # 기본 지도 세팅 (Day 0 상태)
        fig_map = go.Figure(
            data=[go.Scattermapbox(
                lat=lats, lon=lons, mode='markers+text',
                marker=dict(size=10, color='red', opacity=0.7),
                text=cities, textposition="bottom right"
            )],
            frames=map_frames # 만들어둔 60장의 프레임 장착!
        )
        
        # 재생/일시정지 버튼 및 타임라인 슬라이더 장착
        fig_map.update_layout(
            mapbox_style="carto-darkmatter",
            mapbox_center={"lat": 35.9, "lon": 127.7}, mapbox_zoom=5.5,
            height=450, margin={"r":0,"t":0,"l":0,"b":0},
            updatemenus=[dict(
                type="buttons", showactive=False,
                y=1.0, x=0.0, # 버튼 위치 지정
                buttons=[
                    dict(label="▶ 재생", method="animate", args=[None, dict(frame=dict(duration=speed_dict[anim_speed], redraw=True), fromcurrent=True)]),
                    dict(label="⏸ 정지", method="animate", args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")])
                ]
            )],
            sliders=[dict(
                steps=[dict(method='animate', args=[[f"{k}"], dict(mode='immediate', frame=dict(duration=300, redraw=True))], label=f"Day {k}") for k in range(61)],
                x=0.1, y=0, len=0.9
            )]
        )
        st.plotly_chart(fig_map, use_container_width=True)

    with chart_col2:
        st.subheader("📈 60일간의 전국 SIRD 추이")
        # 선 그래프는 시간에 따른 전체 변화를 한눈에 볼 수 있도록 스태틱하게 출력
        days = list(range(61))
        fig_graph = go.Figure()
        fig_graph.add_trace(go.Scatter(x=days, y=history_I, mode='lines', name='감염자(I)', line=dict(color='red', width=3)))
        fig_graph.add_trace(go.Scatter(x=days, y=history_R, mode='lines', name='회복자(R)', line=dict(color='green')))
        fig_graph.add_trace(go.Scatter(x=days, y=history_D, mode='lines', name='사망자(D)', line=dict(color='gray')))
        fig_graph.update_layout(
            height=450, margin={"r":0,"t":10,"l":0,"b":0}, template="plotly_dark",
            xaxis_title="시간 (Day)", yaxis_title="인구 수"
        )
        st.plotly_chart(fig_graph, use_container_width=True)
else:
    # 초기 화면 (버튼 누르기 전) 안내문
    st.info("👈 왼쪽 통제실에서 변수를 설정하고 '시뮬레이션 데이터 생성' 버튼을 눌러주세요.")