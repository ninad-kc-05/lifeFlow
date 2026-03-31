(function () {
    "use strict";

    var routeRoleMap = {
        "admin-dashboard.html": "admin",
        "admin-inventory.html": "admin",
        "admin-reports.html": "admin",
        "admin-requests.html": "admin",
        "admin-users.html": "admin",
        "available_donors.html": "admin",

        "receiver-dashboard.html": "receiver",
        "receiver-inventory.html": "receiver",
        "receiver-request.html": "receiver",
        "receiver-requests.html": "receiver",
        "allocated_patient_details.html": "receiver",

        "donor-dashboard.html": "donor",
        "donor-history.html": "donor",
        "donor-profile.html": "donor",
        "donor_gets_request.html": "donor",
        "status.html": "donor",
        "survey_form.html": "donor"
    };

    function currentPageName() {
        var path = String(window.location.pathname || "");
        var last = path.split("/").pop() || "";
        return last.toLowerCase();
    }

    function redirectHome() {
        window.location.replace("index.html");
    }

    function isAuthorized(requiredRole) {
        var currentRole = localStorage.getItem("userRole");
        return currentRole === requiredRole;
    }

    function enforce() {
        var page = currentPageName();
        var requiredRole = routeRoleMap[page];

        if (!requiredRole) {
            return true;
        }

        if (!isAuthorized(requiredRole)) {
            redirectHome();
            return false;
        }

        return true;
    }

    window.LifeFlowAuth = {
        enforce: enforce,
        redirectHome: redirectHome
    };

    // Initial load guard
    enforce();

    // Guards for history/back-forward cache restore flows
    window.addEventListener("pageshow", function () {
        enforce();
    });

    window.addEventListener("popstate", function () {
        enforce();
    });

    document.addEventListener("visibilitychange", function () {
        if (document.visibilityState === "visible") {
            enforce();
        }
    });
})();
