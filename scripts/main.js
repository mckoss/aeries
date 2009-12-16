// PagesLike.com main.js
// Copyright (c) Mike Koss (mckoss@startpad.org)

global_namespace.Define('pageslike', function(NS) {
	var Timer = NS.Import('startpad.timer');

NS.Extend(NS, {
	sSiteName: "PagesLike",
	sCSRF: "",
	apikey: undefined,
	msLoaded: Timer.MSNow(),

Init: function(sCSRF)
	{
	NS.sCSRF = sCSRF;
	}	
});});