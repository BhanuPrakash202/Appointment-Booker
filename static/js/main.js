$(function () {
  const $form = $("#appointmentForm");
  if ($form.length) {
    const $alert = $("#formAlert");
    function setAlert(kind, text) {
      $alert.removeClass("d-none alert-danger alert-success").addClass("alert alert-" + kind).hide().fadeIn(120).text(text);
    }
    function showFieldError(fieldId, message) {
      const $input = $("#" + fieldId);
      const $err = $("#err-" + fieldId);
      $input.addClass("is-invalid");
      $err.text(message || "").removeClass("d-none").hide().slideDown(120);
    }
    function clearFieldError(fieldId) {
      const $input = $("#" + fieldId);
      const $err = $("#err-" + fieldId);
      $input.removeClass("is-invalid");
      $err.addClass("d-none").text("");
    }
    function isValidEmail(v) { return /\S+@\S+\.\S+/.test(v); }
    function isDateFuture(d) {
      if (!d) return false; const today = new Date(); today.setHours(0,0,0,0); const dt = new Date(d + "T00:00:00"); return !isNaN(dt.getTime()) && dt.getTime() >= today.getTime();
    }
    function isWorkingTime(t) { return t && t >= "09:00" && t <= "17:00"; }

    ["name","email","date","time","reason"].forEach(function (fid) {
      $("#" + fid).on("input change blur", function () { clearFieldError(fid); });
    });

    $form.on("submit", function (e) {
      // Client-side validation before hitting Flask
      const name = $("#name").val().trim();
      const email = $("#email").val().trim();
      const dateStr = $("#date").val();
      const timeStr = $("#time").val();
      const reason = $("#reason").val().trim();

      let ok = true; ["name","email","date","time","reason"].forEach(clearFieldError);
      if (!name) { showFieldError("name","Name is required."); ok = false; }
      if (!email || !isValidEmail(email)) { showFieldError("email","Enter a valid email address."); ok = false; }
      if (!isDateFuture(dateStr)) { showFieldError("date","Date cannot be in the past."); ok = false; }
      if (!isWorkingTime(timeStr)) { showFieldError("time","Time must be between 09:00 and 17:00."); ok = false; }
      if (!reason) { showFieldError("reason","Reason is required."); ok = false; }

      if (!ok) {
        e.preventDefault();
        setAlert("danger", "Please fix the errors and try again.");
      }
    });
  }
});


