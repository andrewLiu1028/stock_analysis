document.addEventListener('DOMContentLoaded', () => {
    const queryBtn = document.getElementById('queryBtn');
    const basicInfoDiv = document.getElementById('basicInfo');
    const gptAnalysisDiv = document.getElementById('gptAnalysis');
    const resultTableDiv = document.getElementById('resultTable');

    let charts = {
        closePrice: null,
        volume: null,
        ma: null,
        kd: null,
        macd: null,
        rsi: null,
    };

    queryBtn?.addEventListener('click', async () => {
        const symbol = document.getElementById('symbol').value.trim();
        const startDate = document.getElementById('start_date').value.trim();
        const endDate = document.getElementById('end_date').value.trim();

        if (!symbol) {
            alert('請輸入股票代碼');
            return;
        }

        const payload = { symbol };
        if (startDate) payload.start_date = startDate;
        if (endDate) payload.end_date = endDate;

        basicInfoDiv.innerHTML = '查詢中...';
        gptAnalysisDiv.innerHTML = 'GPT分析中...';
        resultTableDiv.innerHTML = '';

        try {
            const response = await fetch('/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                throw new Error('伺服器回傳錯誤');
            }

            const data = await response.json();
            console.log('Data received from backend:', data);

            if (data.error) {
                basicInfoDiv.innerHTML = `<p style="color:red;">錯誤: ${data.error}</p>`;
                gptAnalysisDiv.innerHTML = '';
                return;
            }

            destroyAllCharts();
            displayBasicInfo(data);
            displayGPTAnalysis(data.gpt_analysis);
            displayTable(data);

            charts.closePrice = createClosePriceChart(data);
            charts.volume = createVolumeBarChart(data);
            charts.ma = createMAChart(data);
            charts.kd = createKDChart(data);
            charts.macd = createMACDChart(data);
            charts.rsi = createRSIChart(data);
        } catch (error) {
            console.error('Error:', error);
            basicInfoDiv.innerHTML = "<p style='color:red;'>發生錯誤，請稍後再試</p>";
            gptAnalysisDiv.innerHTML = "<p style='color:red;'>無法取得GPT分析結果</p>";
        }
    });

    function destroyAllCharts() {
        for (let key in charts) {
            if (charts[key]) {
                charts[key].destroy();
                charts[key] = null;
            }
        }
    }

    function formatDate(dateStr) {
        const d = new Date(dateStr);
        const yyyy = d.getFullYear();
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const dd = String(d.getDate()).padStart(2, '0');
        return `${yyyy}${mm}${dd}`;
    }

    function displayBasicInfo(data) {
        const { indicators } = data;
        const vol = indicators.volatility ? `${indicators.volatility.toFixed(2)}%` : 'N/A';
        const pct = indicators.percent_change ? `${indicators.percent_change.toFixed(2)}%` : 'N/A';

        basicInfoDiv.innerHTML = `
            <h3>基本資訊</h3>
            <p><strong>年化波動率:</strong> ${vol}</p>
            <p><strong>區間報酬:</strong> ${pct}</p>
        `;
    }

    function displayGPTAnalysis(analysis) {
        if (!analysis) {
            gptAnalysisDiv.innerHTML = "<p style='color:red;'>無法取得GPT分析結果</p>";
            return;
        }

        // 將換行符轉換為HTML的換行和段落
        const formattedAnalysis = analysis
            .split('\n')
            .filter(line => line.trim() !== '')
            .map(line => {
                // 如果行以數字和點開始（如 "1."），將其設為標題樣式
                if (/^\d+\./.test(line)) {
                    return `<h4 class="analysis-title">${line}</h4>`;
                }
                return `<p>${line}</p>`;
            })
            .join('');

        gptAnalysisDiv.innerHTML = `
            <div class="gpt-analysis-content">
                ${formattedAnalysis}
            </div>
        `;
    }

    function displayTable(data) {
        const { stock_data, indicators, signals } = data;

        let html = '<table>';
        html += `
            <tr>
                <th>日期</th>
                <th>Open</th>
                <th>High</th>
                <th>Low</th>
                <th>Close</th>
                <th>Volume</th>
                <th>MA5</th>
                <th>MA20</th>
                <th>MA60</th>
                <th>KD (K/D)</th>
                <th>MACD</th>
                <th>RSI</th>
                <th>買賣訊號</th>
            </tr>`;

        stock_data.forEach((row, index) => {
            const kdValue = `${indicators.k[index]?.toFixed(2) || 'N/A'} / ${indicators.d[index]?.toFixed(2) || 'N/A'}`;
            const macdValue = indicators.macd[index]?.toFixed(2) || 'N/A';
            const rsiValue = indicators.rsi[index]?.toFixed(2) || 'N/A';
            const ma5 = indicators.ma5[index]?.toFixed(2) || 'N/A';
            const ma20 = indicators.ma20[index]?.toFixed(2) || 'N/A';
            const ma60 = indicators.ma60[index]?.toFixed(2) || 'N/A';

            const kdSignal = signals.kd.find(s => s.position === index)?.type || '';
            const maSignal = signals.ma.find(s => s.position === index)?.type || '';
            const macdSignal = signals.macd.find(s => s.position === index)?.type || '';
            const rsiSignal = signals.rsi.find(s => s.position === index)?.type || '';

            const signalMarker = `${kdSignal ? `KD: ${kdSignal}` : ''} ${maSignal ? `MA: ${maSignal}` : ''} ${macdSignal ? `MACD: ${macdSignal}` : ''} ${rsiSignal ? `RSI: ${rsiSignal}` : ''}`;

            html += `
                <tr>
                    <td>${formatDate(row.Date)}</td>
                    <td>${row.Open.toFixed(2)}</td>
                    <td>${row.High.toFixed(2)}</td>
                    <td>${row.Low.toFixed(2)}</td>
                    <td>${row.Close.toFixed(2)}</td>
                    <td>${row.Volume.toLocaleString()}</td>
                    <td>${ma5}</td>
                    <td>${ma20}</td>
                    <td>${ma60}</td>
                    <td>${kdValue}</td>
                    <td>${macdValue}</td>
                    <td>${rsiValue}</td>
                    <td>${signalMarker}</td>
                </tr>`;
        });
        html += '</table>';
        resultTableDiv.innerHTML = html;
    }

    function createClosePriceChart(data) {
        const ctx = document.getElementById('closePriceChart').getContext('2d');
        const labels = data.stock_data.map((d) => formatDate(d.Date));
        const closePrices = data.stock_data.map((d) => d.Close);

        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{ label: 'Close Price', data: closePrices, borderColor: 'blue', fill: false }],
            },
            options: { responsive: true },
        });
    }

    function createVolumeBarChart(data) {
        const ctx = document.getElementById('volumeChart').getContext('2d');
        const labels = data.stock_data.map((d) => formatDate(d.Date));
        const volumes = data.stock_data.map((d) => d.Volume);

        return new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    { label: 'Volume', data: volumes, backgroundColor: 'rgba(0, 123, 255, 0.7)' },
                ],
            },
            options: { responsive: true },
        });
    }

    function createMAChart(data) {
        const ctx = document.getElementById('maChart').getContext('2d');
        const labels = data.stock_data.map((d) => formatDate(d.Date));
        const { ma5, ma20, ma60 } = data.indicators;

        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    { label: 'MA5', data: ma5, borderColor: 'orange', fill: false },
                    { label: 'MA20', data: ma20, borderColor: 'blue', fill: false },
                    { label: 'MA60', data: ma60, borderColor: 'purple', fill: false },
                ],
            },
            options: { responsive: true },
        });
    }

    function createKDChart(data) {
        const ctx = document.getElementById('kdChart').getContext('2d');
        const labels = data.stock_data.map((d) => formatDate(d.Date));
        const { k, d } = data.indicators;

        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    { label: 'K', data: k, borderColor: 'green', fill: false },
                    { label: 'D', data: d, borderColor: 'red', fill: false },
                ],
            },
            options: { responsive: true },
        });
    }

    function createMACDChart(data) {
        const ctx = document.getElementById('macdChart').getContext('2d');
        const labels = data.stock_data.map((d) => formatDate(d.Date));
        const { macd, macd_signal } = data.indicators;

        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    { label: 'MACD', data: macd, borderColor: 'blue', fill: false },
                    { label: 'Signal', data: macd_signal, borderColor: 'orange', fill: false },
                ],
            },
            options: { responsive: true },
        });
    }

    function createRSIChart(data) {
        const ctx = document.getElementById('rsiChart').getContext('2d');
        const labels = data.stock_data.map((d) => formatDate(d.Date));
        const rsi = data.indicators.rsi;

        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{ label: 'RSI', data: rsi, borderColor: 'purple', fill: false }],
            },
            options: { responsive: true },
        });
    }

    const signupForm = document.getElementById("signupForm");
    const signupButton = document.getElementById("signupButton");

    let isSignupValid;
    signupForm?.addEventListener("submit", (e) => {
        const inputs = signupForm.querySelectorAll(".input-field");

        // Check for empty fields
        inputs.forEach((input) => {
        if (input.value.trim() === "") {
            isSignupValid = false;
            input.style.borderColor = "var(--danger-color)";
            input.nextElementSibling?.remove(); // Remove old error message
            const error = document.createElement("p");
            error.style.color = "var(--danger-color)";
            error.textContent = `${input.name} cannot be empty`;
            input.insertAdjacentElement("afterend", error);
        } else {
            input.style.borderColor = "var(--border-light)";
            input.nextElementSibling?.remove(); // Remove error message
            isSignupValid = true;
        }
        });

        if (!isSignupValid) {
            e.preventDefault();
        }
    });

    signupButton?.addEventListener("click", () => {
        if (isSignupValid) {
            signupButton.classList.add("loading");
            setTimeout(() => signupButton.classList.remove("loading"), 2000);
        }
    });

    const loginForm = document.getElementById("loginForm");
    const loginButton = document.getElementById("loginButton");

    let isLoginValid;
    loginForm?.addEventListener("submit", (e) => {
        const inputs = loginForm.querySelectorAll(".input-field");

        // Validate inputs
        inputs.forEach((input) => {
        if (input.value.trim() === "") {
            isLoginValid = false;
            input.style.borderColor = "var(--danger-color)";
            input.nextElementSibling?.remove(); // Remove old error messages
            const error = document.createElement("p");
            error.style.color = "var(--danger-color)";
            error.textContent = `${input.name} cannot be empty`;
            input.insertAdjacentElement("afterend", error);
        } else {
            input.style.borderColor = "var(--border-light)";
            input.nextElementSibling?.remove(); // Remove error messages
            isLoginValid = true;
        }
        });

        // Prevent form submission if invalid
        if (!isLoginValid) {
            e.preventDefault();
        }
    });

    // Simulate button loading state
    loginButton?.addEventListener("click", () => {
        if (isLoginValid) {
            loginButton.classList.add("loading");
            setTimeout(() => loginButton.classList.remove("loading"), 2000); // Simulate loading
        }
    });

});