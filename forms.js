'use strict';
(() => {
  const form = document.querySelector('.native-form');
  if (!form) return;
  const inputPanel = form.querySelector('[data-input-panel]');
  const confirmation = form.querySelector('[data-confirm-panel]');
  const review = form.querySelector('[data-review]');
  const send = form.querySelector('[data-send]');
  const date = form.querySelector('[data-visit-date]');
  const time = form.querySelector('[data-visit-time]');
  // Source booking form's holiday calendar and numeric option mapping, retained.
  const holidays = new Set(['2026-01-01','2026-01-12','2026-02-11','2026-02-23','2026-03-20','2026-04-29','2026-05-03','2026-05-04','2026-05-05','2026-05-06','2026-07-20','2026-08-11','2026-09-21','2026-09-22','2026-09-23','2026-10-12','2026-11-03','2026-11-23','2027-01-01','2027-01-11','2027-02-11','2027-02-23','2027-03-21','2027-03-22','2027-04-29','2027-05-03','2027-05-04','2027-05-05','2027-07-19','2027-08-11','2027-09-20','2027-09-23','2027-10-11','2027-11-03','2027-11-23']);
  const japanToday = () => new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
  function validateDate(rebuild = false) {
    if (!date) return;
    date.min = japanToday();
    date.setCustomValidity('');
    if (!date.value) return;
    const day = new Date(date.value + 'T12:00:00Z').getUTCDay();
    if (date.value < date.min) date.setCustomValidity('今日以降の日付を選択してください。');
    else if (day === 4) date.setCustomValidity('木曜日はノースタッフデーです。別の日を選択してください。');
    else if (form.dataset.kind === 'trial' && date.value === date.min) date.setCustomValidity('当日の体験は 029-839-2339 へお電話ください。');
    const end = day === 0 || day === 6 || holidays.has(date.value) || Number(date.value.slice(0, 4)) > 2027 ? 16 : 20;
    if (rebuild) {
      const prior = time.value;
      time.replaceChildren(new Option('選択してください', ''));
      for (let hour = 10; hour <= end; hour++) time.add(new Option(hour === 10 && form.dataset.kind === 'trial' ? '10:15' : `${hour}:00`, String(hour - 10)));
      if ([...time.options].some(option => option.value === prior)) time.value = prior;
    }
    time.setCustomValidity(time.value && Number(time.value) > end - 10 ? 'この日の受付時間を選び直してください。' : '');
  }
  review.textContent = '入力内容を確認する';
  if (date) {
    validateDate(true);
    date.addEventListener('change', () => validateDate(true));
    time.addEventListener('change', () => validateDate());
  }
  function edit() {
    inputPanel.hidden = false;
    confirmation.hidden = true;
    review.focus();
  }
  form.querySelector('[data-edit]').addEventListener('click', edit);
  form.addEventListener('submit', event => {
    event.preventDefault();
    validateDate();
    if (!form.reportValidity()) return;
    const summary = form.querySelector('.form-summary');
    summary.replaceChildren();
    for (const control of inputPanel.querySelectorAll('input, select, textarea')) {
      if (control.type === 'hidden') continue;
      const label = form.querySelector(`label[for="${control.id}"]`) || control.closest('label');
      if (!label) continue;
      const dt = document.createElement('dt');
      const dd = document.createElement('dd');
      dt.textContent = label.textContent.trim();
      dd.textContent = control.type === 'checkbox' ? '同意しました' : control.tagName === 'SELECT' ? control.selectedOptions[0].textContent : control.value || '入力なし';
      summary.append(dt, dd);
    }
    inputPanel.hidden = true;
    confirmation.hidden = false;
    form.querySelector('#confirm-title').focus();
  });
  let sending = false;
  send.addEventListener('click', () => {
    if (sending) return;
    validateDate();
    if (!form.checkValidity()) { edit(); form.reportValidity(); return; }
    sending = true;
    send.disabled = true;
    form.querySelector('[data-edit]').disabled = true;
    form.querySelector('[data-send-status]').textContent = '受付サービスへ送信しています。結果画面をご確認ください。';
    HTMLFormElement.prototype.submit.call(form);
  });
  window.addEventListener('pageshow', () => {
    sending = false;
    send.disabled = false;
    form.querySelector('[data-edit]').disabled = false;
    form.querySelector('[data-send-status]').textContent = '';
  });
})();
