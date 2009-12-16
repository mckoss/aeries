//--------------------------------------------------------------------------
// PagesLike functions
//--------------------------------------------------------------------------
global_namespace.Define('pageslike.widget', function(NS) {
	var Base = NS.Import('startpad.base');
	var DOM = NS.Import('startpad.DOM');
	var Event = NS.Import('startpad.events');
	var Format = NS.Import('startpad.format-util');
	var Data = NS.Import('startpad.data');

NS.Extend(NS, {
	sSiteName: "PagesLike",
	mTestDomains: {
		'devserver': true,
		'localhost': true,
		'pageslike': true,
		'localhost:8080': true
		},
	sDomain: "www.pageslike.com",
	iWidget: 0,
	aWidgets: [],
	optionsDefault: {community: 'general'},
	fStyled: false,
	
Init: function()
	{
	// For debug versions - send requests to local server
	if (window.location.host in NS.mTestDomains)
		NS.sDomain = window.location.host;
	},
	
InsertWidget: function(options)
	{
	// TODO: Create version which can insert in DOM AFTER page load

	if (!NS.fStyled)
		{
		var head = document.getElementsByTagName("head")[0];         
		var link = document.createElement('link');
		link.type = 'text/css';
		link.rel = 'stylesheet';
		link.href = 'http://' + NS.sDomain + '/styles/widget.css';
		head.appendChild(link);
		NS.fStyled = true;
		}
	
	return new Widget(options);
	},
	
GetWidget: function(iWidget)
	{
	var widget = NS.aWidgets[iWidget];
	widget.Update();
	return widget;
	},
	
ScanPage: function(elemRoot)
	{
	reHead = /^H[1-8]$/i;
	reTagClass = /\btag\b/i;
	reBookmarkClass = /\bbookmark\b/i;
	var aInfo = [];
	
	if (!elemRoot)
		elemRoot = document;
	
	var aAnchors = elemRoot.getElementsByTagName('a');
	var aTags = [];
	var aBookmarks = [];
	for (var i = 0; i < aAnchors.length; i++)
		{
		var anchor = aAnchors[i];
		var sRel = anchor.getAttribute('rel');
		if (reTagClass.test(sRel))
			aTags.push(anchor);
		if (reBookmarkClass(sRel))
			aBookmarks.push(anchor);
		}
	
	// Blogger-type page - use bookmarks and tags to find structure
	if (aBookmarks.length > 0)
		{
		for (var i = 0; i < aBookmarks.length; i++)
			{
			var bookmark = aBookmarks[i]; 
			var info = {url: bookmark.href, tags:[]};
			aInfo.push(info);
			}
		
		aTitles = DOM.GetElementsByTagClassName(elemRoot, "*", "post-title");
		
		for (var i = 0; i < aTitles.length; i++)
			{
			var title = aTitles[i];
			var sTitle = DOM.GetText(title);
			var iBM = NS.ClosestAncestor(title, aBookmarks);
			aInfo[iBM].title = sTitle;
			}
	
		// Match up corresponding Titles, tags, and bookmarks (permalinks)
		for (var i = 0; i < aTags.length; i++)
			{
			var tag = aTags[i];
			var sTag = NS.TagFromElem(tag);
			if (sTag == undefined)
				continue;
			var iBM = NS.ClosestAncestor(tag, aBookmarks);
			aInfo[iBM].tags.push(sTag);
			}
		}

	
	// Look for "Wordpress style" page of articles
	// <h><a>title</a></h>...<a rel='tag'>tag-name</a>
	// ... special case for TechFlash:
	// <p class='titlePost'><a>title</a></p> ... <p class='tags'><a>tag-name</a>
	if (aInfo.length == 0)
		{
		NS.ScanDOM(elemRoot, function(elem, iDepth) {
			if (elem.tagName == 'A' &&
				(reHead.test(elem.parentNode.tagName) ||
				 elem.parentNode.tagName == 'P' && elem.parentNode.className == 'titlePost'))
				{
				if (!elem.href)
					return false;
				var info = {
					url: elem.href,
					title: DOM.GetText(elem),
					tags: []
					};
				aInfo.push(info);
				return false;
				}
			// Apply tag to more recent story link
			if (aInfo.length > 0 && elem.tagName == 'A' &&
				(reTagClass.test(elem.getAttribute('rel')) ||
				 elem.parentNode.tagName == 'P' && elem.parentNode.className == 'tags'))
				{
				aInfo[aInfo.length-1].tags.push(NS.TagFromElem(elem))
				}
			return false;
			});
		}

	if (aInfo.length == 0)
		{
		// Treat page as a single subject page w/o internal structure
		var info = {
			url: document.location.href,
			title: document.title,
			tags: NS.ExtractTags(aTags)
			};
		
		// In some cases, a page heading is a better title for the post (document titles sometimes
		// contain (redundant) site name information.
		var aHeads = document.getElementsByTagName('h1');
		if (aHeads.length == 1)
			{
			var sTitle;
			sTitle = DOM.GetText(aHeads[0]);
			if (sTitle)
				info.title = sTitle;
			}
		aInfo.push(info);
		}

	for (var i = 0; i < aInfo.length; i++)
		{
		Base.DeDupArray(aInfo[i].tags);
		}
	return aInfo;
	},
	
ClosestAncestor: function(elemChild, aUncles)
	{
	var cBest;
	var iBest;
	for (var i = 0; i < aUncles.length; i++)
		{
		var c = DOM.CommonAncestorHeight(elemChild, aUncles[i]);
		if (cBest === undefined || c < cBest)
			{
			iBest = i;
			cBest = c;
			}
		}
	return iBest;
	},

ScanDOM: function(elem, fn, iDepth)
	{
	if (!elem)
		elem = document;
	
	if (iDepth === undefined)
		iDepth = 0;
	
	if (elem.nodeType == 1 && fn(elem, iDepth))
		return true;
	
	var aChildren = elem.childNodes;
	for (var i = 0; i < aChildren.length; i++)
		{
		if (NS.ScanDOM(aChildren[i], fn, iDepth+1))
			return true;
		}
	return false;
	},
	
ExtractTags: function(aTags)
	{
	var aSTags = [];
	for (var i = 0; i < aTags.length; i++)
		{
		var tag = aTags[i];
		var sTag = NS.TagFromElem(tag);
		if (sTag == undefined)
			continue;
		aSTags.push(sTag);
		}
	},
	
TagFromElem: function(elem)
	{
	var sTag = DOM.GetText(elem);
	if (!sTag)
		return undefined;
	sTag = Format.Slugify(sTag);
	return sTag;
	}
});

// Widget @constructor
function Widget(options)
{
	NS.aWidgets[this.iWidget = NS.iWidget++] = this;

	this.options = Base.ExtendMissing(options, NS.optionsDefault);
	this.options.iWidget = this.iWidget;
	
	this.Insert();

	if (!this.options.defer_load)
		Event.AddEventFn(window, "load", this.Fill.FnMethod(this));
}

NS.Extend(Widget.prototype, {
	sWidgetPattern: '<div class="pageslike override" id="pageslike_{iWidget}"><h4>Pages Like This</h4>Loading...</div>',
	sHeader: '<h4>Pages Like This</h4>',
	sTagsPattern: '<p class="tags">{tags}</p>',
	sLinksPattern: '<ul class="list">{links}</ul>',
	sLinkPattern: '<li {li_class}><a href="{url}">{title} ({score})</a></li>',
	sTagPattern: '<a href="http://{sDomain}/tag/{tag}">{tag}</a>',
	sFooter: '<p class="poweredby">Powered by <a href="http://{sDomain}/">{sSiteName}</a></p>',
	nLinksDisplayed: 7,

Insert: function()
	{
	// We don't natively use 'override' - so the destination page can style any element and
	// get priority in their local css style sheet.
	var sHTML = Format.ReplaceKeys(this.sWidgetPattern, this.options);
	
	if (this.elem)
		this.elem.innerHTML = sHTML;
	else
		document.write(sHTML);
	},
	
Update: function()
	{
	if (this.div == undefined)
		this.div = document.getElementById("pageslike_" + this.iWidget);
	},
	
Fill: function(evt, elemRoot, fnCallback)
	{
	console.log("PagesLike - Loading widget: ", this);
	var aInfo = NS.ScanPage(elemRoot);
	// Loose the this point on callbacks - use closure value
	var widget = this;
	widget.Update();
	
	Data.GetAPIKey(NS.sDomain, function (obj)
		{
		var data = new Data.ScriptData("http://" + NS.sDomain + "/scan.json");
		data.Call(NS.Extend({links:aInfo}, widget.options), function (obj)
			{
			widget.scan = obj;
			var sHTML = new Base.StBuf();
			
			// Header
			sHTML.Append(Format.ReplaceKeys(widget.sHeader, NS));
	
			if (obj.status != 'OK')
				{
				sHTML.Append(obj.message);
				}
			else
				{
				// Tags
				sTagList = new Base.StBuf();
				var sSep = '';
				for (var i = 0; i < obj.tags.length; i++)
					{
					var tag = obj.tags[i];
					sTagList.Append(sSep + Format.ReplaceKeys(widget.sTagPattern,
								{sDomain: NS.sDomain, tag: tag}));
					sSep = ', ';
					}
				sHTML.Append(Format.ReplaceKeys(widget.sTagsPattern, {tags:sTagList}));
	
				// Links
				sLinkList = new Base.StBuf();
				for (var i = 0; i < obj.links.length; i++)
					{
					var link = obj.links[i];
					if (i > widget.nLinksDisplayed)
						NS.Extend(link, {li_class:'class="extra"'});
					sLinkList.Append(Format.ReplaceKeys(widget.sLinkPattern, link));
					}
				sHTML.Append(Format.ReplaceKeys(widget.sLinksPattern, {links:sLinkList}));
				}
			
			// Footer
			sHTML.Append(Format.ReplaceKeys(widget.sFooter, NS));	
			widget.div.innerHTML = sHTML.toString();
			
			// Remove the 'extra' class from <li> elements if we have fewer than the
			// desired minimum number of links.
			var links = widget.div.getElementsByTagName('li');
			var cVisible = 0
			for (i = 0; i < links.length; i++)
				{
				if (cVisible >= widget.nLinksDisplayed)
					break;
				if (links[i].offsetHeight != 0)
					{
					cVisible++;
					continue;
					}
				if (links[i].className == 'extra')
					{
					links[i].className = '';
					if (links[i].offsetHeight != 0)
						cVisible++;
					}
				}
			
			if (fnCallback)
				fnCallback(obj);
			});
		});

	}
});

NS.Init();
}); // pageslike.widget
