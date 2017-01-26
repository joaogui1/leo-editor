# -*- coding: utf-8 -*-
#@+leo-ver=5-thin
#@+node:ekr.20140827092102.18574: * @file leoColorizer.py
#@@first
'''All colorizing code for Leo.'''
#@+<< imports >>
#@+node:ekr.20140827092102.18575: ** << imports >> (leoColorizer.py)
import leo.core.leoGlobals as g
from leo.core.leoQt import Qsci, QtGui, QtWidgets # isQt5, QtCore,
# try:
    # import builtins # Python 3
# except ImportError:
    # import __builtin__ as builtins # Python 2.
import re
import string
import time
#@-<< imports >>
#@+others
#@+node:ekr.20140906081909.18690: ** class ColorizerMixin
class ColorizerMixin(object):
    '''A mixin class for all c.frame.body.colorizer classes.'''

    def __init__(self, c):
        '''Ctor for ColorizerMixin class.'''
        self.c = c

    def colorize(self, p, incremental=False, interruptable=True):
        assert False, 'colorize must be defined in sublcasses'

    ### To be removed.
    def kill(self):
        '''Kill colorizing.'''
        pass

    #@+others
    #@+node:ekr.20140906081909.18715: *3* cm.findColorDirectives
    color_directives_pat = re.compile(
        # Order is important: put longest matches first.
        r'(^@color|^@killcolor|^@nocolor-node|^@nocolor)'
        , re.MULTILINE)

    def findColorDirectives(self, p):
        '''
        Scan p for @color, @killcolor, @nocolor and @nocolor-node directives.

        Return a dict containing pointers to the start of each directive.
        '''
        trace = False and not g.unitTesting
        d = {}
        anIter = self.color_directives_pat.finditer(p.b)
        for m in anIter:
            # Remove leading '@' for compatibility with
            # functions in leoGlobals.py.
            word = m.group(0)[1:]
            d[word] = word
        if trace: g.trace(d)
        return d
    #@+node:ekr.20140906081909.18701: *3* cm.findLanguageDirectives
    def findLanguageDirectives(self, p):
        '''Scan p's body text for *valid* @language directives.

        Return a list of languages.'''
        # Speed not very important: called only for nodes containing @language directives.
        trace = False and not g.unitTesting
        aList = []
        for s in g.splitLines(p.b):
            if g.match_word(s, 0, '@language'):
                i = len('@language')
                i = g.skip_ws(s, i)
                j = g.skip_id(s, i)
                if j > i:
                    word = s[i: j]
                    if self.isValidLanguage(word):
                        aList.append(word)
                    else:
                        if trace: g.trace('invalid', word)
        if trace: g.trace(aList)
        return aList
    #@+node:ekr.20140906081909.18702: *3* cm.isValidLanguage
    def isValidLanguage(self, language):
        fn = g.os_path_join(g.app.loadDir, '..', 'modes', '%s.py' % (language))
        return g.os_path_exists(fn)
    #@+node:ekr.20140906081909.18711: *3* cm.scanColorByPosition
    def scanColorByPosition(self, p):
        '''Scan p for color-related directives.'''
        c = self.c
        wrapper = c.frame.body.wrapper
        i = wrapper.getInsertPoint()
        s = wrapper.getAllText()
        i1, i2 = g.getLine(s, i)
        tag = '@language'
        language = self.language
        for s in g.splitLines(s[: i1]):
            if s.startswith(tag):
                language = s[len(tag):].strip()
        return language
    #@+node:ekr.20140906081909.18697: *3* cm.scanColorDirectives
    def scanColorDirectives(self, p):
        '''Set self.language based on the directives in p's tree.'''
        trace = False and not g.unitTesting
        c = self.c
        if not c:
            assert False, g.callers()
            return None # self.c may be None for testing.
        root = p.copy()
        self.colorCacheFlag = False
        self.language = None
        self.rootMode = None # None, "code" or "doc"
        for p in root.self_and_parents():
            theDict = g.get_directives_dict(p)
            # if trace: g.trace(p.h,theDict)
            if p == root:
                # The @colorcache directive is a per-node directive.
                self.colorCacheFlag = 'colorcache' in theDict
                # g.trace('colorCacheFlag: %s' % self.colorCacheFlag)
            if 'language' in theDict:
                s = theDict["language"]
                aList = self.findLanguageDirectives(p)
                # In the root node, we use the first (valid) @language directive,
                # no matter how many @language directives the root node contains.
                # In ancestor nodes, only unambiguous @language directives
                # set self.language.
                if p == root or len(aList) == 1:
                    self.languageList = list(set(aList))
                    self.language = aList and aList[0] or []
                    break
            if 'root' in theDict and not self.rootMode:
                s = theDict["root"]
                if g.match_word(s, 0, "@root-code"):
                    self.rootMode = "code"
                elif g.match_word(s, 0, "@root-doc"):
                    self.rootMode = "doc"
                else:
                    doc = c.config.at_root_bodies_start_in_doc_mode
                    self.rootMode = "doc" if doc else "code"
        # If no language, get the language from any @<file> node.
        if self.language:
            if trace: g.trace('found @language %s %s' % (self.language, self.languageList))
            return self.language
        #  Attempt to get the language from the nearest enclosing @<file> node.
        self.language = g.getLanguageFromAncestorAtFileNode(root)
        if not self.language:
            if trace: g.trace('using default', c.target_language)
            self.language = c.target_language
        return self.language # For use by external routines.
    #@+node:ekr.20140906081909.18704: *3* cm.updateSyntaxColorer
    def updateSyntaxColorer(self, p):
        '''Scan p.b for color directives.'''
        trace = False and not g.unitTesting
        # An important hack: shortcut everything if the first line is @killcolor.
        if p.b.startswith('@killcolor'):
            if trace: g.trace('@killcolor')
            self.flag = False
            return self.flag
        else:
            # self.flag is True unless an unambiguous @nocolor is seen.
            p = p.copy()
            self.flag = self.useSyntaxColoring(p)
            self.scanColorDirectives(p) # Sets self.language
        if trace: g.trace(self.flag, len(p.b), self.language, p.h, g.callers(5))
        return self.flag
    #@+node:ekr.20140906081909.18714: *3* cm.useSyntaxColoring
    def useSyntaxColoring(self, p):
        """Return True unless p is unambiguously under the control of @nocolor."""
        trace = False and not g.unitTesting
        if not p:
            if trace: g.trace('no p', repr(p))
            return False
        p = p.copy()
        first = True; kind = None; val = True
        self.killColorFlag = False
        for p in p.self_and_parents():
            d = self.findColorDirectives(p)
            color, no_color = 'color' in d, 'nocolor' in d
            # An @nocolor-node in the first node disabled coloring.
            if first and 'nocolor-node' in d:
                kind = '@nocolor-node'
                self.killColorFlag = True
                val = False; break
            # A killcolor anywhere disables coloring.
            elif 'killcolor' in d:
                kind = '@killcolor %s' % p.h
                self.killColorFlag = True
                val = False; break
            # A color anywhere in the target enables coloring.
            elif color and first:
                kind = 'color %s' % p.h
                val = True; break
            # Otherwise, the @nocolor specification must be unambiguous.
            elif no_color and not color:
                kind = '@nocolor %s' % p.h
                val = False; break
            elif color and not no_color:
                kind = '@color %s' % p.h
                val = True; break
            first = False
        if trace: g.trace(val, kind)
        return val
    #@-others
#@+node:ekr.20110605121601.18569: ** class JEditColorizer
# This is c.frame.body.colorizer.highlighter.colorer
class JEditColorizer(object):
    '''
    This class contains jEdit pattern matchers adapted
    for use with QSyntaxHighlighter.
    '''
    #@+<< about the line-oriented jEdit colorizer >>
    #@+node:ekr.20110605121601.18570: *3* << about the line-oriented jEdit colorizer >>
    #@@nocolor-node
    #@+at
    # The aha behind the line-oriented jEdit colorizer is that we can define one or
    # more *restarter* methods for each pattern matcher that could possibly match
    # across line boundaries. I say "one or more" because we need a separate restarter
    # method for all combinations of arguments that can be passed to the jEdit pattern
    # matchers. In effect, these restarters are lambda bindings for the generic
    # restarter methods.
    # 
    # In actuality, very few restarters are needed. For example, for Python, we need
    # restarters for continued strings, and both flavors of continued triple-quoted
    # strings. For python, these turn out to be three separate lambda bindings for
    # restart_match_span.
    # 
    # When a jEdit pattern matcher partially succeeds, it creates the lambda binding
    # for its restarter and calls setRestart to set the ending state of the present
    # line to an integer representing the bound restarter. setRestart calls
    # computeState to create a *string* representing the lambda binding of the
    # restarter. setRestart then calls stateNameToStateNumber to convert that string
    # to an integer state number that then gets passed to Qt's setCurrentBlockState.
    # The string is useful for debugging; Qt only uses the corresponding number.
    #@-<< about the line-oriented jEdit colorizer >>
    #@+others
    #@+node:ekr.20110605121601.18571: *3*  jedit.Birth & init
    #@+node:ekr.20110605121601.18572: *4* jedit.ctor
    def __init__(self, c, colorizer, highlighter, wrapper):
        '''Ctor for JEditColorizer class.'''
        assert highlighter, g.callers()
        # Basic data...
        self.c = c
        self.colorizer = colorizer
        self.highlighter = highlighter # a QSyntaxHighlighter
        self.p = None
        self.wrapper = wrapper
        assert(wrapper == self.c.frame.body.wrapper)
        # Used by recolor and helpers...
        self.actualColorDict = {} # Used only by setTag.
        self.defaultLanguage = None
        self.hyperCount = 0
        self.nextState = 1 # Dont use 0.
        self.restartDict = {} # Keys are state numbers, values are restart functions.
        self.stateDict = {} # Keys are state numbers, values state names.
        self.stateNameDict = {} # Keys are state names, values are state numbers.
        # Attributes dict ivars: defaults are as shown...
        self.default = 'null'
        self.digit_re = ''
        self.escape = ''
        self.highlight_digits = True
        self.ignore_case = True
        self.no_word_sep = ''
        # Config settings...
        self.showInvisibles = c.config.getBool("show_invisibles_by_default")
        self.colorizer.showInvisibles = self.showInvisibles
        # g.trace(self.showInvisibles)
            # Also set in init().
        self.underline_undefined = c.config.getBool("underline_undefined_section_names")
        self.use_hyperlinks = c.config.getBool("use_hyperlinks")
        # Debugging...
        self.count = 0 # For unit testing.
        self.allow_mark_prev = True # The new colorizer tolerates this nonsense :-)
        self.n_setTag = 0
        self.tagCount = 0
        self.trace = False or c.config.getBool('trace_colorizer')
        self.trace_leo_matches = False
        self.trace_match_flag = False
            # True: trace all matching methods.
            # This isn't so useful now that colorRangeWithTag shows g.callers(2).
        self.verbose = False
        # Profiling...
        self.recolorCount = 0 # Total calls to recolor
        self.stateCount = 0 # Total calls to setCurrentState
        self.totalStates = 0
        self.maxStateNumber = 0
        self.totalKeywordsCalls = 0
        self.totalLeoKeywordsCalls = 0
        # Mode data...
        self.defaultRulesList = []
        self.importedRulesets = {}
        self.prev = None # The previous token.
        self.fonts = {} # Keys are config names.  Values are actual fonts.
        self.keywords = {} # Keys are keywords, values are 0..5.
        self.language_name = None # The name of the language for the current mode.
        self.last_language = None # The language for which configuration tags are valid.
        self.modes = {} # Keys are languages, values are modes.
        self.mode = None # The mode object for the present language.
        self.modeBunch = None # A bunch fully describing a mode.
        self.modeStack = []
        self.rulesDict = {}
        # self.defineAndExtendForthWords()
        self.word_chars = {} # Inited by init_keywords().
        self.setFontFromConfig()
        self.tags = [
            # 8 Leo-specific tags.
            "blank", # show_invisibles_space_color
            "docpart",
            "leokeyword",
            "link",
            "name",
            "namebrackets",
            "tab", # show_invisibles_space_color
            "url",
            # jEdit tags.
            'comment1', 'comment2', 'comment3', 'comment4',
            # default, # exists, but never generated.
            'function',
            'keyword1', 'keyword2', 'keyword3', 'keyword4',
            'label', 'literal1', 'literal2', 'literal3', 'literal4',
            'markup', 'operator',
        ]
        self.defineLeoKeywordsDict()
        self.defineDefaultColorsDict()
        self.defineDefaultFontDict()
    #@+node:ekr.20110605121601.18573: *5* jedit.defineLeoKeywordsDict
    def defineLeoKeywordsDict(self):
        self.leoKeywordsDict = {}
        for key in g.globalDirectiveList:
            self.leoKeywordsDict[key] = 'leokeyword'
    #@+node:ekr.20110605121601.18574: *5* jedit.defineDefaultColorsDict
    #@@nobeautify

    def defineDefaultColorsDict (self):

        # These defaults are sure to exist.
        self.default_colors_dict = {

            # Used in Leo rules...

            # tag name      :( option name,                  default color),
            'blank'         :('show_invisibles_space_color', '#E5E5E5'), # gray90
            'docpart'       :('doc_part_color',              'red'),
            'leokeyword'    :('leo_keyword_color',           'blue'),
            'link'          :('section_name_color',          'red'),
            'name'          :('undefined_section_name_color','red'),
            'namebrackets'  :('section_name_brackets_color', 'blue'),
            'tab'           :('show_invisibles_tab_color',   '#CCCCCC'), # gray80
            'url'           :('url_color',                   'purple'),

            # Used by the old colorizer: to be removed.

            # 'bracketRange'   :('bracket_range_color',     'orange'), # Forth.
            # 'comment'        :('comment_color',           'red'),
            # 'cwebName'       :('cweb_section_name_color', 'red'),
            # 'keyword'        :('keyword_color',           'blue'),
            # 'latexBackground':('latex_background_color',  'white'),
            # 'pp'             :('directive_color',         'blue'),
            # 'string'         :('string_color',            '#00aa00'), # Used by IDLE.

            # jEdit tags.
            # tag name  :( option name,     default color),
            'comment1'  :('comment1_color', 'red'),
            'comment2'  :('comment2_color', 'red'),
            'comment3'  :('comment3_color', 'red'),
            'comment4'  :('comment4_color', 'red'),
            'function'  :('function_color', 'black'),
            'keyword1'  :('keyword1_color', 'blue'),
            'keyword2'  :('keyword2_color', 'blue'),
            'keyword3'  :('keyword3_color', 'blue'),
            'keyword4'  :('keyword4_color', 'blue'),
            'keyword5'  :('keyword5_color', 'blue'),
            'label'     :('label_color',    'black'),
            'literal1'  :('literal1_color', '#00aa00'),
            'literal2'  :('literal2_color', '#00aa00'),
            'literal3'  :('literal3_color', '#00aa00'),
            'literal4'  :('literal4_color', '#00aa00'),
            'markup'    :('markup_color',   'red'),
            'null'      :('null_color',     None), #'black'),
            'operator'  :('operator_color', 'black'), # 2014/09/17
        }
    #@+node:ekr.20110605121601.18575: *5* jedit.defineDefaultFontDict
    #@@nobeautify

    def defineDefaultFontDict (self):

        self.default_font_dict = {

            # Used in Leo rules...

                # tag name      : option name
                'blank'         :'show_invisibles_space_font', # 2011/10/24.
                'docpart'       :'doc_part_font',
                'leokeyword'    :'leo_keyword_font',
                'link'          :'section_name_font',
                'name'          :'undefined_section_name_font',
                'namebrackets'  :'section_name_brackets_font',
                'tab'           : 'show_invisibles_tab_font', # 2011/10/24.
                'url'           : 'url_font',

            # Used by old colorizer.

                # 'bracketRange'   :'bracketRange_font', # Forth.
                # 'comment'       :'comment_font',
                # 'cwebName'      :'cweb_section_name_font',
                # 'keyword'       :'keyword_font',
                # 'latexBackground':'latex_background_font',
                # 'pp'            :'directive_font',
                # 'string'        :'string_font',

             # jEdit tags.

                 # tag name     : option name
                'comment1'      :'comment1_font',
                'comment2'      :'comment2_font',
                'comment3'      :'comment3_font',
                'comment4'      :'comment4_font',
                #'default'       :'default_font',
                'function'      :'function_font',
                'keyword1'      :'keyword1_font',
                'keyword2'      :'keyword2_font',
                'keyword3'      :'keyword3_font',
                'keyword4'      :'keyword4_font',
                'keyword5'      :'keyword5_font',
                'label'         :'label_font',
                'literal1'      :'literal1_font',
                'literal2'      :'literal2_font',
                'literal3'      :'literal3_font',
                'literal4'      :'literal4_font',
                'markup'        :'markup_font',
                # 'nocolor' This tag is used, but never generates code.
                'null'          :'null_font',
                'operator'      :'operator_font',
        }
    #@+node:ekr.20110605121601.18576: *4* jedit.addImportedRules
    def addImportedRules(self, mode, rulesDict, rulesetName):
        '''Append any imported rules at the end of the rulesets specified in mode.importDict'''
        if self.importedRulesets.get(rulesetName):
            return
        else:
            self.importedRulesets[rulesetName] = True
        names = hasattr(mode, 'importDict') and mode.importDict.get(rulesetName, []) or []
        for name in names:
            savedBunch = self.modeBunch
            ok = self.init_mode(name)
            if ok:
                rulesDict2 = self.rulesDict
                for key in rulesDict2.keys():
                    aList = self.rulesDict.get(key, [])
                    aList2 = rulesDict2.get(key)
                    if aList2:
                        # Don't add the standard rules again.
                        rules = [z for z in aList2 if z not in aList]
                        if rules:
                            # g.trace([z.__name__ for z in rules])
                            aList.extend(rules)
                            self.rulesDict[key] = aList
            # g.trace('***** added rules for %s from %s' % (name,rulesetName))
            self.initModeFromBunch(savedBunch)
    #@+node:ekr.20110605121601.18577: *4* jedit.addLeoRules
    def addLeoRules(self, theDict):
        '''Put Leo-specific rules to theList.'''
        # pylint: disable=no-member
        # Python 2 uses rule.im_func. Python 3 uses rule.__func__.
        table = (
            # Rules added at front are added in **reverse** order.
            ('@', self.match_leo_keywords, True), # Called after all other Leo matchers.
                # Debatable: Leo keywords override langauge keywords.
            ('@', self.match_at_color, True),
            ('@', self.match_at_killcolor, True),
            ('@', self.match_at_language, True), # 2011/01/17
            ('@', self.match_at_nocolor, True),
            ('@', self.match_at_nocolor_node, True),
            ('@', self.match_at_wrap, True), # 2015/06/22
            ('@', self.match_doc_part, True),
            ('f', self.match_url_f, True),
            ('g', self.match_url_g, True),
            ('h', self.match_url_h, True),
            ('m', self.match_url_m, True),
            ('n', self.match_url_n, True),
            ('p', self.match_url_p, True),
            ('t', self.match_url_t, True),
            ('w', self.match_url_w, True),
            ('<', self.match_section_ref, True), # Called **first**.
            # Rules added at back are added in normal order.
            (' ', self.match_blanks, False),
            ('\t', self.match_tabs, False),
        )
        for ch, rule, atFront, in table:
            # Replace the bound method by an unbound method.
            if g.isPython3:
                rule = rule.__func__
            else:
                rule = rule.im_func
            # g.trace(rule)
            theList = theDict.get(ch, [])
            if rule not in theList:
                if atFront:
                    theList.insert(0, rule)
                else:
                    theList.append(rule)
                theDict[ch] = theList
        # g.trace(g.listToString(theDict.get('@')))
    #@+node:ekr.20111024091133.16702: *4* jedit.configure_hard_tab_width
    def configure_hard_tab_width(self):
        '''Set the width of a hard tab.
        The stated default is 40, but apparently it must be set explicitly.
        '''
        trace = False and not g.unitTesting
        c, wrapper = self.c, self.wrapper
        # For some reason, the size is not accurate.
        font = wrapper.widget.currentFont()
        info = QtGui.QFontInfo(font)
        size = info.pointSizeF()
        pixels_per_point = 1.0 # 0.9
        hard_tab_width = abs(int(pixels_per_point * size * c.tab_width))
        if trace: g.trace(
            'family', font.family(), 'point size', size,
            'tab_width', c.tab_width,
            'hard_tab_width', hard_tab_width)
        wrapper.widget.setTabStopWidth(hard_tab_width)
    #@+node:ekr.20110605121601.18578: *4* jedit.configure_tags
    def configure_tags(self):
        '''Configure all tags.'''
        trace = False and not g.unitTesting
        traceColors = True
        traceFonts = False
        c = self.c
        wrapper = self.wrapper
        isQt = g.app.gui.guiName().startswith('qt')
        if trace: g.trace(self.colorizer.language)
        if wrapper and hasattr(wrapper, 'start_tag_configure'):
            wrapper.start_tag_configure()
        # Get the default body font.
        defaultBodyfont = self.fonts.get('default_body_font')
        if not defaultBodyfont:
            defaultBodyfont = c.config.getFontFromParams(
                "body_text_font_family", "body_text_font_size",
                "body_text_font_slant", "body_text_font_weight",
                c.config.defaultBodyFontSize)
            self.fonts['default_body_font'] = defaultBodyfont
        # Configure fonts.
        if trace and traceFonts: g.trace('*' * 10, 'configuring fonts')
        keys = list(self.default_font_dict.keys()); keys.sort()
        for key in keys:
            option_name = self.default_font_dict[key]
            # First, look for the language-specific setting, then the general setting.
            for name in ('%s_%s' % (self.colorizer.language, option_name), (option_name)):
                if trace and traceFonts: g.trace(name)
                font = self.fonts.get(name)
                if font:
                    if trace and traceFonts:
                        g.trace('**found', name, id(font))
                    wrapper.tag_configure(key, font=font)
                    break
                else:
                    family = c.config.get(name + '_family', 'family')
                    size = c.config.get(name + '_size', 'size')
                    slant = c.config.get(name + '_slant', 'slant')
                    weight = c.config.get(name + '_weight', 'weight')
                    if family or slant or weight or size:
                        family = family or g.app.config.defaultFontFamily
                        size = size or c.config.defaultBodyFontSize
                        slant = slant or 'roman'
                        weight = weight or 'normal'
                        font = g.app.gui.getFontFromParams(family, size, slant, weight)
                        # Save a reference to the font so it 'sticks'.
                        self.fonts[key] = font
                        if trace and traceFonts:
                            g.trace('**found', key, name, family, size, slant, weight, id(font))
                        wrapper.tag_configure(key, font=font)
                        break
            else: # Neither the general setting nor the language-specific setting exists.
                if list(self.fonts.keys()): # Restore the default font.
                    if trace and traceFonts:
                        g.trace('default', key, font)
                    self.fonts[key] = font # Essential
                    wrapper.tag_configure(key, font=defaultBodyfont)
                else:
                    if trace and traceFonts:
                        g.trace('no fonts')
            if isQt and key == 'url' and font:
                font.setUnderline(True)
        keys = sorted(self.default_colors_dict.keys())
        for name in keys:
            option_name, default_color = self.default_colors_dict[name]
            color = (
                c.config.getColor('%s_%s' % (self.colorizer.language, option_name)) or
                c.config.getColor(option_name) or
                default_color)
            if trace and traceColors: g.trace(option_name, color)
            # Must use foreground, not fg.
            try:
                wrapper.tag_configure(name, foreground=color)
            except Exception: # Recover after a user error.
                g.es_exception()
                wrapper.tag_configure(name, foreground=default_color)
        # underline=var doesn't seem to work.
        if 0: # self.use_hyperlinks: # Use the same coloring, even when hyperlinks are in effect.
            wrapper.tag_configure("link", underline=1) # defined
            wrapper.tag_configure("name", underline=0) # undefined
        else:
            wrapper.tag_configure("link", underline=0)
            if self.underline_undefined:
                wrapper.tag_configure("name", underline=1)
            else:
                wrapper.tag_configure("name", underline=0)
        self.configure_variable_tags()
        try:
            wrapper.end_tag_configure()
        except AttributeError:
            pass
    #@+node:ekr.20110605121601.18579: *4* jedit.configure_variable_tags
    def configure_variable_tags(self):
        c = self.c
        wrapper = self.wrapper
        for name, option_name, default_color in (
            # ("blank", "show_invisibles_space_background_color", "Gray90"),
            # ("tab", "show_invisibles_tab_background_color", "Gray80"),
            ("elide", None, "yellow"),
        ):
            if self.showInvisibles:
                color = option_name and c.config.getColor(option_name) or default_color
            else:
                option_name, default_color = self.default_colors_dict.get(name, (None, None),)
                color = option_name and c.config.getColor(option_name) or ''
            try:
                wrapper.tag_configure(name, background=color)
            except Exception: # A user error.
                wrapper.tag_configure(name, background=default_color)
        # Special case:
        if not self.showInvisibles:
            wrapper.tag_configure("elide", elide="1")
    #@+node:ekr.20110605121601.18580: *4* jedit.init
    def init(self, p, s):
        '''
        Init the colorizer.
        Old: called from leo_h.rehighlight.
        New: called from colorizer.colorize
        '''
        trace = False and not g.unitTesting
        if p: self.p = p.copy()
        self.all_s = s or ''
        if trace: g.trace('(jEdit)', self.colorizer.language, p.h)
        # State info.
        self.all_s = s
        self.global_i, self.global_j = 0, 0
        self.global_offset = 0
        # These *must* be recomputed.
        self.nextState = 1 # Dont use 0.
        self.stateDict = {}
        self.stateNameDict = {}
        self.restartDict = {}
        self.init_mode(self.colorizer.language)
        self.clearState()
        self.showInvisibles = self.colorizer.showInvisibles
            # The show/hide-invisible commands changes this.
        # Used by matchers.
        self.prev = None
        if self.last_language != self.colorizer.language:
            # Must be done to support per-language @font/@color settings.
            self.configure_tags()
            self.last_language = self.colorizer.language
        self.configure_hard_tab_width() # 2011/10/04
    #@+node:ekr.20110605121601.18581: *4* jedit.init_mode & helpers
    def init_mode(self, name):
        '''Name may be a language name or a delegate name.'''
        trace = False and not g.unitTesting
        if name:
            if trace: g.trace(name)
        else:
            if trace: g.trace('no name')
            return False
        language, rulesetName = self.nameToRulesetName(name)
        bunch = self.modes.get(rulesetName)
        if bunch:
            if bunch.language == 'unknown-language':
                if trace: g.trace('found unknown language')
                return False
            else:
                if trace: g.trace('found', language, rulesetName)
                self.initModeFromBunch(bunch)
                self.language_name = language # 2011/05/30
                return True
        else:
            if trace: g.trace(language, rulesetName)
            # Bug fix: 2008/2/10: Don't try to import a non-existent language.
            path = g.os_path_join(g.app.loadDir, '..', 'modes')
            fn = g.os_path_join(path, '%s.py' % (language))
            if g.os_path_exists(fn):
                mode = g.importFromPath(moduleName=language, path=path)
                if trace: g.trace(mode)
            else:
                mode = None
            return self.init_mode_from_module(name, mode)
    #@+node:btheado.20131124162237.16303: *5* jedit.init_mode_from_module
    def init_mode_from_module(self, name, mode):
        '''Name may be a language name or a delegate name.
           Mode is a python module or class containing all
           coloring rule attributes for the mode.
        '''
        trace = False and not g.unitTesting
        if trace: g.trace(g.callers())
        language, rulesetName = self.nameToRulesetName(name)
        if mode:
            # A hack to give modes/forth.py access to c.
            if hasattr(mode, 'pre_init_mode'):
                mode.pre_init_mode(self.c)
        else:
            # Create a dummy bunch to limit recursion.
            self.modes[rulesetName] = self.modeBunch = g.Bunch(
                attributesDict={},
                defaultColor=None,
                keywordsDict={},
                language='unknown-language',
                mode=mode,
                properties={},
                rulesDict={},
                rulesetName=rulesetName,
                word_chars=self.word_chars, # 2011/05/21
            )
            if trace: g.trace('***** No colorizer file: %s.py' % language)
            self.rulesetName = rulesetName
            self.language_name = 'unknown-language'
            return False
        self.colorizer.language = language
        self.rulesetName = rulesetName
        self.properties = hasattr(mode, 'properties') and mode.properties or {}
        self.keywordsDict = hasattr(mode, 'keywordsDictDict') and mode.keywordsDictDict.get(rulesetName, {}) or {}
        self.setKeywords()
        self.attributesDict = hasattr(mode, 'attributesDictDict') and mode.attributesDictDict.get(rulesetName) or {}
        # if trace: g.trace(rulesetName,self.attributesDict)
        self.setModeAttributes()
        self.rulesDict = hasattr(mode, 'rulesDictDict') and mode.rulesDictDict.get(rulesetName) or {}
        # if trace: g.trace(self.rulesDict)
        self.addLeoRules(self.rulesDict)
        self.defaultColor = 'null'
        self.mode = mode
        self.modes[rulesetName] = self.modeBunch = g.Bunch(
            attributesDict=self.attributesDict,
            defaultColor=self.defaultColor,
            keywordsDict=self.keywordsDict,
            language=self.colorizer.language,
            mode=self.mode,
            properties=self.properties,
            rulesDict=self.rulesDict,
            rulesetName=self.rulesetName,
            word_chars=self.word_chars, # 2011/05/21
        )
        # Do this after 'officially' initing the mode, to limit recursion.
        self.addImportedRules(mode, self.rulesDict, rulesetName)
        self.updateDelimsTables()
        initialDelegate = self.properties.get('initialModeDelegate')
        if initialDelegate:
            if trace: g.trace('initialDelegate', initialDelegate)
            # Replace the original mode by the delegate mode.
            self.init_mode(initialDelegate)
            language2, rulesetName2 = self.nameToRulesetName(initialDelegate)
            self.modes[rulesetName] = self.modes.get(rulesetName2)
            self.language_name = language2 # 2011/05/30
        else:
            self.language_name = language # 2011/05/30
        return True
    #@+node:ekr.20110605121601.18582: *5* jedit.nameToRulesetName
    def nameToRulesetName(self, name):
        '''
        Compute language and rulesetName from name, which is either a language
        name or a delegate name.
        '''
        if not name:
            return ''
        i = name.find('::')
        if i == -1:
            language = name
            # New in Leo 5.0: allow delegated language names.
            language = g.app.delegate_language_dict.get(language, language)
            rulesetName = '%s_main' % (language)
        else:
            language = name[: i]
            delegate = name[i + 2:]
            rulesetName = self.munge('%s_%s' % (language, delegate))
        # if rulesetName == 'php_main': rulesetName = 'php_php'
        # g.trace(name,language,rulesetName)
        return language, rulesetName
    #@+node:ekr.20110605121601.18583: *5* jedit.setKeywords
    def setKeywords(self):
        '''Initialize the keywords for the present language.

         Set self.word_chars ivar to string.letters + string.digits
         plus any other character appearing in any keyword.
         '''
        # Add any new user keywords to leoKeywordsDict.
        d = self.keywordsDict
        keys = list(d.keys())
        for s in g.globalDirectiveList:
            key = '@' + s
            if key not in keys:
                d[key] = 'leokeyword'
        # Create a temporary chars list.  It will be converted to a dict later.
        chars = [g.toUnicode(ch) for ch in (string.ascii_letters + string.digits)]
        for key in list(d.keys()):
            for ch in key:
                if ch not in chars:
                    chars.append(g.toUnicode(ch))
        # jEdit2Py now does this check, so this isn't really needed.
        # But it is needed for forth.py.
        for ch in (' ', '\t'):
            if ch in chars:
                # g.es_print('removing %s from word_chars' % (repr(ch)))
                chars.remove(ch)
        # g.trace(self.colorizer.language,[str(z) for z in chars])
        # Convert chars to a dict for faster access.
        self.word_chars = {}
        for z in chars:
            self.word_chars[z] = z
        # g.trace(sorted(self.word_chars.keys()))
    #@+node:ekr.20110605121601.18584: *5* jedit.setModeAttributes
    def setModeAttributes(self):
        '''Set the ivars from self.attributesDict,
        converting 'true'/'false' to True and False.'''
        d = self.attributesDict
        aList = (
            ('default', 'null'),
            ('digit_re', ''),
            ('escape', ''), # New in Leo 4.4.2.
            ('highlight_digits', True),
            ('ignore_case', True),
            ('no_word_sep', ''),
        )
        # g.trace(d)
        for key, default in aList:
            val = d.get(key, default)
            if val in ('true', 'True'): val = True
            if val in ('false', 'False'): val = False
            setattr(self, key, val)
            # g.trace(key,val)
    #@+node:ekr.20110605121601.18585: *5* jedit.initModeFromBunch
    def initModeFromBunch(self, bunch):
        self.modeBunch = bunch
        self.attributesDict = bunch.attributesDict
        self.setModeAttributes()
        self.defaultColor = bunch.defaultColor
        self.keywordsDict = bunch.keywordsDict
        self.colorizer.language = bunch.language
        self.mode = bunch.mode
        self.properties = bunch.properties
        self.rulesDict = bunch.rulesDict
        self.rulesetName = bunch.rulesetName
        self.word_chars = bunch.word_chars # 2011/05/21
    #@+node:ekr.20110605121601.18586: *5* jedit.updateDelimsTables
    def updateDelimsTables(self):
        '''Update g.app.language_delims_dict if no entry for the language exists.'''
        d = self.properties
        lineComment = d.get('lineComment')
        startComment = d.get('commentStart')
        endComment = d.get('commentEnd')
        if lineComment and startComment and endComment:
            delims = '%s %s %s' % (lineComment, startComment, endComment)
        elif startComment and endComment:
            delims = '%s %s' % (startComment, endComment)
        elif lineComment:
            delims = '%s' % lineComment
        else:
            delims = None
        if delims:
            d = g.app.language_delims_dict
            if not d.get(self.colorizer.language):
                d[self.colorizer.language] = delims
                # g.trace(self.colorizer.language,'delims:',repr(delims))
    #@+node:ekr.20110605121601.18587: *4* jedit.munge
    def munge(self, s):
        '''Munge a mode name so that it is a valid python id.'''
        valid = string.ascii_letters + string.digits + '_'
        return ''.join([ch.lower() if ch in valid else '_' for ch in s])
    #@+node:ekr.20110605121601.18588: *4* jedit.setFontFromConfig
    def setFontFromConfig(self):
        c = self.c
        self.bold_font = c.config.getFontFromParams(
            "body_text_font_family", "body_text_font_size",
            "body_text_font_slant", "body_text_font_weight",
            c.config.defaultBodyFontSize)
        self.italic_font = c.config.getFontFromParams(
            "body_text_font_family", "body_text_font_size",
            "body_text_font_slant", "body_text_font_weight",
            c.config.defaultBodyFontSize)
        self.bolditalic_font = c.config.getFontFromParams(
            "body_text_font_family", "body_text_font_size",
            "body_text_font_slant", "body_text_font_weight",
            c.config.defaultBodyFontSize)
        self.color_tags_list = []
    #@+node:ekr.20110605121601.18589: *3*  jedit.Pattern matchers
    #@+node:ekr.20110605121601.18590: *4*  About the pattern matchers
    #@@nocolor-node
    #@+at
    # 
    # The following jEdit matcher methods return the length of the matched text if the
    # match succeeds, and zero otherwise. In most cases, these methods colorize all
    # the matched text.
    # 
    # The following arguments affect matching:
    # 
    # - at_line_start         True: sequence must start the line.
    # - at_whitespace_end     True: sequence must be first non-whitespace text of the line.
    # - at_word_start         True: sequence must start a word.
    # - hash_char             The first character that must match in a regular expression.
    # - no_escape:            True: ignore an 'end' string if it is preceded by
    #                         the ruleset's escape character.
    # - no_line_break         True: the match will not succeed across line breaks.
    # - no_word_break:        True: the match will not cross word breaks.
    # 
    # The following arguments affect coloring when a match succeeds:
    # 
    # - delegate              A ruleset name. The matched text will be colored recursively
    #                         by the indicated ruleset.
    # - exclude_match         If True, the actual text that matched will not be colored.
    # - kind                  The color tag to be applied to colored text.
    #@+node:ekr.20110605121601.18591: *4* jedit.dump
    def dump(self, s):
        if s.find('\n') == -1:
            return s
        else:
            return '\n' + s + '\n'
    #@+node:ekr.20110605121601.18592: *4* jedit.Leo rule functions
    #@+node:ekr.20110605121601.18593: *5* jedit.match_at_color
    def match_at_color(self, s, i):
        if self.trace_leo_matches: g.trace()
        # Only matches at start of line.
        if i == 0 and g.match_word(s, 0, '@color'):
            self.colorizer.flag = True # Enable coloring.
                ### Has no effect.
            n = self.setRestart(self.restartColor)
            self.setState(n)
                # Enables coloring of *this* line.
            self.colorRangeWithTag(s, 0, len('@color'), 'leokeyword')
                # Now required. Sets state.
            return len('@color')
        else:
            return 0
    #@+node:ekr.20170125140113.1: *6* restartColor
    def restartColor(self, s):
        '''Change all lines up to the next color directive.'''
        # if self.trace_leo_matches: g.trace(repr(s))
        if g.match_word(s, 0, '@killcolor'):
            self.colorRangeWithTag(s, 0, len('@color'), 'leokeyword')
            self.setRestart(self.restartKillColor)
            return -len(s) # Continue to suppress coloring.
        elif g.match_word(s, 0, '@nocolor-node'):
            self.setRestart(self.restartNoColorNode)
            return -len(s) # Continue to suppress coloring.
        elif g.match_word(s, 0, '@nocolor'):
            self.setRestart(self.restartNoColor)
            return -len(s) # Continue to suppress coloring.
        else:
            n = self.setRestart(self.restartColor)
            self.setState(n) # Enables coloring of *this* line.
            return 0 # Allow colorizing!
    #@+node:ekr.20110605121601.18594: *5* jedit.match_at_language
    def match_at_language(self, s, i):
        '''Match Leo's @language directive.'''
        trace = (False or self.trace_leo_matches) and not g.unitTesting
        if trace: g.trace(i, repr(s))
        seq = '@language'
        # Only matches at start of line.
        if i != 0: return 0
        if g.match_word(s, i, seq):
            j = i + len(seq)
            j = g.skip_ws(s, j)
            k = g.skip_c_id(s, j)
            name = s[j: k]
            ok = self.init_mode(name)
            if trace: g.trace(ok, name, self.language_name)
            if ok:
                self.colorRangeWithTag(s, i, k, 'leokeyword')
            return k - i
        else:
            return 0
    #@+node:ekr.20110605121601.18595: *5* jedit.match_at_nocolor & restarter
    def match_at_nocolor(self, s, i):
        if self.trace_leo_matches: g.trace(i, repr(s))
        # Only matches at start of line.
        if i == 0 and not g.match(s, i, '@nocolor-') and g.match_word(s, i, '@nocolor'):
            self.setRestart(self.restartNoColor)
            return len(s) # Match everything.
        else:
            return 0
    #@+node:ekr.20110605121601.18596: *6* jedit.restartNoColor
    def restartNoColor(self, s):
        if self.trace_leo_matches: g.trace(repr(s))
        if g.match_word(s, 0, '@color'):
            n = self.setRestart(self.restartColor)
            self.setState(n) # Enables coloring of *this* line.
            self.colorRangeWithTag(s, 0, len('@color'), 'leokeyword')
            return len('@color')
        else:
            self.setRestart(self.restartNoColor)
            return len(s) # Match everything.
    #@+node:ekr.20110605121601.18597: *5* jedit.match_at_killcolor & restarter
    def match_at_killcolor(self, s, i):
        # if self.trace_leo_matches: g.trace(i, repr(s))
        # Only matches at start of line.
        if i == 0 and g.match_word(s, i, '@killcolor'):
            self.setRestart(self.restartKillColor)
            return len(s) # Match everything.
        else:
            return 0
    #@+node:ekr.20110605121601.18598: *6* jedit.restartKillColor
    def restartKillColor(self, s):
        self.setRestart(self.restartKillColor)
        return len(s) + 1
    #@+node:ekr.20110605121601.18599: *5* jedit.match_at_nocolor_node & restarter
    def match_at_nocolor_node(self, s, i):
        # if self.trace_leo_matches: g.trace()
        # Only matches at start of line.
        if i == 0 and g.match_word(s, i, '@nocolor-node'):
            self.setRestart(self.restartNoColorNode)
            return len(s) # Match everything.
        else:
            return 0
    #@+node:ekr.20110605121601.18600: *6* jedit.restartNoColorNode
    def restartNoColorNode(self, s):
        self.setRestart(self.restartNoColorNode)
        return len(s) + 1
    #@+node:ekr.20150622072456.1: *5* jedit.match_at_wrap
    def match_at_wrap(self, s, i):
        '''Match Leo's @wrap directive.'''
        c = self.c
        trace = (False or self.trace_leo_matches) and not g.unitTesting
        if trace: g.trace(i, repr(s))
        # Only matches at start of line.
        seq = '@wrap'
        if i == 0 and g.match_word(s, i, seq):
            j = i + len(seq)
            k = g.skip_ws(s, j)
            self.colorRangeWithTag(s, i, k, 'leokeyword')
            ### self.clearState()
            c.frame.setWrap(c.p, force=True)
            return k - i
        else:
            return 0
    #@+node:ekr.20110605121601.18601: *5* jedit.match_blanks
    def match_blanks(self, s, i):
        if 1: # Use Qt code to show invisibles.
            return 0
        else: # Old code...
            if not self.showInvisibles:
                return 0
            j = i; n = len(s)
            while j < n and s[j] == ' ':
                j += 1
            if j > i:
                self.colorRangeWithTag(s, i, j, 'blank')
                return j - i
            else:
                return 0
    #@+node:ekr.20110605121601.18602: *5* jedit.match_doc_part & restarter
    def match_doc_part(self, s, i):
        '''
        Colorize Leo's @ and @ doc constructs.
        Matches only at the start of the line.
        '''
        if i != 0:
            return 0
        elif g.match_word(s, i, '@doc'):
            j = i + 4
        elif g.match(s, i, '@') and (i + 1 >= len(s) or s[i + 1] in (' ', '\t', '\n')):
            j = i + 1
        else:
            return 0
        self.colorRangeWithTag(s, i, j, 'leokeyword')
        self.colorRangeWithTag(s, j, len(s), 'docpart')
        self.setRestart(self.restartDocPart)
        return len(s)
    #@+node:ekr.20110605121601.18603: *6* jedit.restartDocPart
    def restartDocPart(self, s):
        '''
        Restarter for @ and @ contructs.
        Continue until an @c, @code or @language at the start of the line.
        '''
        for tag in ('@c', '@code', '@language'):
            if g.match_word(s, 0, tag):
                if tag == '@language':
                    return self.match_at_language(s, 0)
                else:
                    j = len(tag)
                    self.colorRangeWithTag(s, 0, j, 'leokeyword') # 'docpart')
                    self.clearState()
                    return j
        self.setRestart(self.restartDocPart)
        self.colorRangeWithTag(s, 0, len(s), 'docpart')
        return len(s)
    #@+node:ekr.20110605121601.18604: *5* jedit.match_leo_keywords
    def match_leo_keywords(self, s, i):
        '''Succeed if s[i:] is a Leo keyword.'''
        # g.trace(i,g.get_line(s,i))
        self.totalLeoKeywordsCalls += 1
        if s[i] != '@':
            return 0
        # fail if something besides whitespace precedes the word on the line.
        i2 = i - 1
        while i2 >= 0:
            ch = s[i2]
            if ch == '\n':
                break
            elif ch in (' ', '\t'):
                i2 -= 1
            else:
                # g.trace('not a word 1',repr(ch))
                return 0
        # Get the word as quickly as possible.
        j = i + 1
        while j < len(s) and s[j] in self.word_chars:
            j += 1
        word = s[i + 1: j] # entries in leoKeywordsDict do not start with '@'.
        if j < len(s) and s[j] not in (' ', '\t', '\n'):
            # g.trace('not a word 2',repr(word))
            return 0 # Fail, but allow a rescan, as in objective_c.
        if self.leoKeywordsDict.get(word):
            kind = 'leokeyword'
            self.colorRangeWithTag(s, i, j, kind)
            self.prev = (i, j, kind)
            result = j - i + 1 # Bug fix: skip the last character.
            self.trace_match(kind, s, i, j)
            # g.trace('*** match',repr(s))
            return result
        else:
            # 2010/10/20: also check the keywords dict here.
            # This allows for objective_c keywords starting with '@'
            # This will not slow down Leo, because it is called
            # for things that look like Leo directives.
            word = '@' + word
            kind = self.keywordsDict.get(word)
            if kind:
                self.colorRangeWithTag(s, i, j, kind)
                self.prev = (i, j, kind)
                self.trace_match(kind, s, i, j)
                # g.trace('found',word)
                return j - i
            else:
                # g.trace('fail',repr(word),repr(self.word_chars))
                return -(j - i + 1) # An important optimization.
    #@+node:ekr.20110605121601.18605: *5* jedit.match_section_ref
    def match_section_ref(self, s, i):
        if self.trace_leo_matches: g.trace()
        c = self.c; p = c.p
        if not g.match(s, i, '<<'):
            return 0
        k = g.find_on_line(s, i + 2, '>>')
        if k == -1:
            return 0
        else:
            j = k + 2
            self.colorRangeWithTag(s, i, i + 2, 'namebrackets')
            # g.trace('ref %r %s' % (s[i: j], p.h))
            # g.trace(g.callers(6))
            ref = g.findReference(c, s[i: j], p)
            if ref:
                if self.use_hyperlinks:
                    #@+<< set the hyperlink >>
                    #@+node:ekr.20110605121601.18606: *6* << set the hyperlink >> (jedit)
                    # Set the bindings to VNode callbacks.
                    tagName = "hyper" + str(self.hyperCount)
                    self.hyperCount += 1
                    ref.tagName = tagName
                    #@-<< set the hyperlink >>
                else:
                    self.colorRangeWithTag(s, i + 2, k, 'link')
            else:
                self.colorRangeWithTag(s, i + 2, k, 'name')
            self.colorRangeWithTag(s, k, j, 'namebrackets')
            return j - i
    #@+node:ekr.20110605121601.18607: *5* jedit.match_tabs
    def match_tabs(self, s, i):
        if 1: # Use Qt code to show invisibles.
            return 0
        else: # Old code...
            if not self.showInvisibles:
                return 0
            if self.trace_leo_matches: g.trace()
            j = i; n = len(s)
            while j < n and s[j] == '\t':
                j += 1
            if j > i:
                self.colorRangeWithTag(s, i, j, 'tab')
                return j - i
            else:
                return 0
    #@+node:ekr.20110605121601.18608: *5* jedit.match_url_any/f/h  (new)
    # Fix bug 893230: URL coloring does not work for many Internet protocols.
    # Added support for: gopher, mailto, news, nntp, prospero, telnet, wais
    url_regex_f = re.compile(r"""(file|ftp)://[^\s'"]+[\w=/]""")
    url_regex_g = re.compile(r"""gopher://[^\s'"]+[\w=/]""")
    url_regex_h = re.compile(r"""(http|https)://[^\s'"]+[\w=/]""")
    url_regex_m = re.compile(r"""mailto://[^\s'"]+[\w=/]""")
    url_regex_n = re.compile(r"""(news|nntp)://[^\s'"]+[\w=/]""")
    url_regex_p = re.compile(r"""prospero://[^\s'"]+[\w=/]""")
    url_regex_t = re.compile(r"""telnet://[^\s'"]+[\w=/]""")
    url_regex_w = re.compile(r"""wais://[^\s'"]+[\w=/]""")
    kinds = '(file|ftp|gopher|http|https|mailto|news|nntp|prospero|telnet|wais)'
    # url_regex   = re.compile(r"""(file|ftp|http|https)://[^\s'"]+[\w=/]""")
    url_regex = re.compile(r"""%s://[^\s'"]+[\w=/]""" % (kinds))

    def match_any_url(self, s, i):
        return self.match_compiled_regexp(s, i, kind='url', regexp=self.url_regex)

    def match_url_f(self, s, i):
        return self.match_compiled_regexp(s, i, kind='url', regexp=self.url_regex_f)

    def match_url_g(self, s, i):
        return self.match_compiled_regexp(s, i, kind='url', regexp=self.url_regex_g)

    def match_url_h(self, s, i):
        return self.match_compiled_regexp(s, i, kind='url', regexp=self.url_regex_h)

    def match_url_m(self, s, i):
        return self.match_compiled_regexp(s, i, kind='url', regexp=self.url_regex_m)

    def match_url_n(self, s, i):
        return self.match_compiled_regexp(s, i, kind='url', regexp=self.url_regex_n)

    def match_url_p(self, s, i):
        return self.match_compiled_regexp(s, i, kind='url', regexp=self.url_regex_p)

    def match_url_t(self, s, i):
        return self.match_compiled_regexp(s, i, kind='url', regexp=self.url_regex_t)

    def match_url_w(self, s, i):
        return self.match_compiled_regexp(s, i, kind='url', regexp=self.url_regex_w)
    #@+node:ekr.20110605121601.18609: *4* jedit.match_compiled_regexp (new)
    def match_compiled_regexp(self, s, i, kind, regexp, delegate=''):
        '''Succeed if the compiled regular expression regexp matches at s[i:].'''
        if self.verbose: g.trace(g.callers(1), i, repr(s[i: i + 20]), 'regexp', regexp)
        # if at_line_start and i != 0 and s[i-1] != '\n': return 0
        # if at_whitespace_end and i != g.skip_ws(s,0): return 0
        # if at_word_start and i > 0 and s[i-1] in self.word_chars: return 0
        n = self.match_compiled_regexp_helper(s, i, regexp)
        if n > 0:
            j = i + n
            assert(j - i == n)
            self.colorRangeWithTag(s, i, j, kind, delegate=delegate)
            self.prev = (i, j, kind)
            self.trace_match(kind, s, i, j)
            return j - i
        else:
            return 0
    #@+node:ekr.20110605121601.18610: *5* jedit.match_compiled_regexp_helper
    def match_compiled_regexp_helper(self, s, i, regex):
        '''Return the length of the matching text if seq (a regular expression) matches the present position.'''
        # Match succeeds or fails more quickly than search.
        self.match_obj = mo = regex.match(s, i) # re_obj.search(s,i)
        if mo is None:
            return 0
        start, end = mo.start(), mo.end()
        if start != i:
            return 0
        # if trace:
            # g.trace('pattern',pattern)
            # g.trace('match: %d, %d, %s' % (start,end,repr(s[start: end])))
            # g.trace('groups',mo.groups())
        return end - start
    #@+node:ekr.20110605121601.18611: *4* jedit.match_eol_span
    def match_eol_span(self, s, i,
        kind=None, seq='',
        at_line_start=False, at_whitespace_end=False, at_word_start=False,
        delegate='', exclude_match=False
    ):
        '''Succeed if seq matches s[i:]'''
        if self.verbose: g.trace(g.callers(1), i, repr(s[i: i + 20]))
        if at_line_start and i != 0 and s[i - 1] != '\n': return 0
        if at_whitespace_end and i != g.skip_ws(s, 0): return 0
        if at_word_start and i > 0 and s[i - 1] in self.word_chars: return 0 # 7/5/2008
        if at_word_start and i + len(seq) + 1 < len(s) and s[i + len(seq)] in self.word_chars:
            return 0
        if g.match(s, i, seq):
            j = len(s)
            self.colorRangeWithTag(s, i, j, kind, delegate=delegate, exclude_match=exclude_match)
            self.prev = (i, j, kind)
            self.trace_match(kind, s, i, j)
            # g.trace(s[i:j])
            return j # (was j-1) With a delegate, this could clear state.
        else:
            return 0
    #@+node:ekr.20110605121601.18612: *4* jedit.match_eol_span_regexp
    def match_eol_span_regexp(self, s, i,
        kind='', regexp='',
        at_line_start=False, at_whitespace_end=False, at_word_start=False,
        delegate='', exclude_match=False
    ):
        '''Succeed if the regular expression regex matches s[i:].'''
        if self.verbose: g.trace(g.callers(1), i, repr(s[i: i + 20]))
        if at_line_start and i != 0 and s[i - 1] != '\n': return 0
        if at_whitespace_end and i != g.skip_ws(s, 0): return 0
        if at_word_start and i > 0 and s[i - 1] in self.word_chars: return 0 # 7/5/2008
        n = self.match_regexp_helper(s, i, regexp)
        if n > 0:
            j = len(s)
            self.colorRangeWithTag(s, i, j, kind, delegate=delegate, exclude_match=exclude_match)
            self.prev = (i, j, kind)
            self.trace_match(kind, s, i, j)
            return j - i
        else:
            return 0
    #@+node:ekr.20110605121601.18613: *4* jedit.match_everything
    # def match_everything (self,s,i,kind=None,delegate='',exclude_match=False):
        # '''Match the entire rest of the string.'''
        # j = len(s)
        # self.colorRangeWithTag(s,i,j,kind,delegate=delegate)
        # return j
    #@+node:ekr.20110605121601.18614: *4* jedit.match_keywords
    # This is a time-critical method.

    def match_keywords(self, s, i):
        '''
        Succeed if s[i:] is a keyword.
        Returning -len(word) for failure greatly reduces the number of times this
        method is called.
        '''
        trace = False and not g.unitTesting
        traceFail = True
        self.totalKeywordsCalls += 1
        # g.trace(i,repr(s[i:]))
        # We must be at the start of a word.
        if i > 0 and s[i - 1] in self.word_chars:
            # if trace: g.trace('not at word start',s[i-1])
            return 0
        # Get the word as quickly as possible.
        j = i; n = len(s)
        chars = self.word_chars
        # 2013/11/04: A kludge just for Haskell:
        if self.language_name == 'haskell':
            chars["'"] = "'"
        while j < n and s[j] in chars:
            j += 1
        word = s[i: j]
        if not word:
            g.trace('can not happen', repr(s[i: max(j, i + 1)]), repr(s[i: i + 10]), g.callers())
            return 0
        if self.ignore_case: word = word.lower()
        kind = self.keywordsDict.get(word)
        if kind:
            self.colorRangeWithTag(s, i, j, kind)
            self.prev = (i, j, kind)
            result = j - i
            if trace: g.trace('success', word, kind, result)
            self.trace_match(kind, s, i, j)
            return result
        else:
            if trace and traceFail: g.trace('fail', word, kind)
            return -len(word) # An important new optimization.
    #@+node:ekr.20110605121601.18615: *4* jedit.match_line
    def match_line(self, s, i, kind=None, delegate='', exclude_match=False):
        '''Match the rest of the line.'''
        j = g.skip_to_end_of_line(s, i)
        self.colorRangeWithTag(s, i, j, kind, delegate=delegate)
        return j - i
    #@+node:ekr.20110605121601.18616: *4* jedit.match_mark_following & getNextToken
    def match_mark_following(self, s, i,
        kind='', pattern='',
        at_line_start=False, at_whitespace_end=False, at_word_start=False,
        exclude_match=False
    ):
        '''Succeed if s[i:] matches pattern.'''
        if not self.allow_mark_prev: return 0
        # g.trace(g.callers(1),i,repr(s[i:i+20]))
        if at_line_start and i != 0 and s[i - 1] != '\n': return 0
        if at_whitespace_end and i != g.skip_ws(s, 0): return 0
        if at_word_start and i > 0 and s[i - 1] in self.word_chars: return 0 # 7/5/2008
        if at_word_start and i + len(pattern) + 1 < len(s) and s[i + len(pattern)] in self.word_chars:
            return 0 # 7/5/2008
        if g.match(s, i, pattern):
            j = i + len(pattern)
            # self.colorRangeWithTag(s,i,j,kind,exclude_match=exclude_match)
            k = self.getNextToken(s, j)
            # 2011/05/31: Do not match *anything* unless there is a token following.
            if k > j:
                self.colorRangeWithTag(s, i, j, kind, exclude_match=exclude_match)
                self.colorRangeWithTag(s, j, k, kind, exclude_match=False)
                j = k
                self.prev = (i, j, kind)
                self.trace_match(kind, s, i, j)
                return j - i
            else:
                return 0
        else:
            return 0
    #@+node:ekr.20110605121601.18617: *5* jedit.getNextToken
    def getNextToken(self, s, i):
        '''Return the index of the end of the next token for match_mark_following.

        The jEdit docs are not clear about what a 'token' is, but experiments with jEdit
        show that token means a word, as defined by word_chars.'''
        # 2011/05/31: Might we extend the concept of token?
        # If s[i] is not a word char, should we return just it?
        while i < len(s) and s[i] in self.word_chars:
            i += 1
        # 2011/05/31: was i+1
        return min(len(s), i)
    #@+node:ekr.20110605121601.18618: *4* jedit.match_mark_previous
    def match_mark_previous(self, s, i,
        kind='', pattern='',
        at_line_start=False, at_whitespace_end=False, at_word_start=False,
        exclude_match=False
    ):
        '''Return the length of a matched SEQ or 0 if no match.

        'at_line_start':    True: sequence must start the line.
        'at_whitespace_end':True: sequence must be first non-whitespace text of the line.
        'at_word_start':    True: sequence must start a word.'''
        # This match was causing most of the syntax-color problems.
        return 0 # 2009/6/23
    #@+node:ekr.20110605121601.18619: *4* jedit.match_regexp_helper
    def match_regexp_helper(self, s, i, pattern):
        '''Return the length of the matching text if seq (a regular expression) matches the present position.'''
        trace = False and not g.unitTesting
        if trace: g.trace('%-10s %-20s %s' % (
            self.colorizer.language, pattern, s)) # g.callers(1)
        try:
            flags = re.MULTILINE
            if self.ignore_case: flags |= re.IGNORECASE
            re_obj = re.compile(pattern, flags)
        except Exception:
            # Do not call g.es here!
            g.trace('Invalid regular expression: %s' % (pattern))
            return 0
        # Match succeeds or fails more quickly than search.
        self.match_obj = mo = re_obj.match(s, i) # re_obj.search(s,i)
        if mo is None:
            return 0
        else:
            start, end = mo.start(), mo.end()
            if start != i: # Bug fix 2007-12-18: no match at i
                return 0
            if trace:
                g.trace('pattern', pattern)
                g.trace('match: %d, %d, %s' % (start, end, repr(s[start: end])))
                g.trace('groups', mo.groups())
            return end - start
    #@+node:ekr.20110605121601.18620: *4* jedit.match_seq
    def match_seq(self, s, i,
        kind='', seq='',
        at_line_start=False,
        at_whitespace_end=False,
        at_word_start=False,
        delegate=''
    ):
        '''Succeed if s[:] mathces seq.'''
        if at_line_start and i != 0 and s[i - 1] != '\n':
            j = i
        elif at_whitespace_end and i != g.skip_ws(s, 0):
            j = i
        elif at_word_start and i > 0 and s[i - 1] in self.word_chars: # 7/5/2008
            j = i
        if at_word_start and i + len(seq) + 1 < len(s) and s[i + len(seq)] in self.word_chars:
            j = i # 7/5/2008
        elif g.match(s, i, seq):
            j = i + len(seq)
            self.colorRangeWithTag(s, i, j, kind, delegate=delegate)
            self.prev = (i, j, kind)
            self.trace_match(kind, s, i, j)
        else:
            j = i
        return j - i
    #@+node:ekr.20110605121601.18621: *4* jedit.match_seq_regexp
    def match_seq_regexp(self, s, i,
        kind='', regexp='',
        at_line_start=False, at_whitespace_end=False, at_word_start=False,
        delegate=''
    ):
        '''Succeed if the regular expression regexp matches at s[i:].'''
        if self.verbose: g.trace(g.callers(1), i, repr(s[i: i + 20]), 'regexp', regexp)
        if at_line_start and i != 0 and s[i - 1] != '\n': return 0
        if at_whitespace_end and i != g.skip_ws(s, 0): return 0
        if at_word_start and i > 0 and s[i - 1] in self.word_chars: return 0
        n = self.match_regexp_helper(s, i, regexp)
        j = i + n
        assert(j - i == n)
        self.colorRangeWithTag(s, i, j, kind, delegate=delegate)
        self.prev = (i, j, kind)
        self.trace_match(kind, s, i, j)
        return j - i
    #@+node:ekr.20110605121601.18622: *4* jedit.match_span & helper & restarter
    def match_span(self, s, i,
        kind='', begin='', end='',
        at_line_start=False, at_whitespace_end=False, at_word_start=False,
        delegate='', exclude_match=False,
        no_escape=False, no_line_break=False, no_word_break=False
    ):
        '''Succeed if s[i:] starts with 'begin' and contains a following 'end'.'''
        trace = False and not g.unitTesting
        dots = False # A flag that we are using dots as a continuation.
        if i >= len(s): return 0
        # g.trace(begin,end,no_escape,no_line_break,no_word_break)
        if at_line_start and i != 0 and s[i - 1] != '\n':
            j = i
        elif at_whitespace_end and i != g.skip_ws(s, 0):
            j = i
        elif at_word_start and i > 0 and s[i - 1] in self.word_chars:
            j = i
        elif at_word_start and i + len(begin) + 1 < len(s) and s[i + len(begin)] in self.word_chars:
            j = i
        elif not g.match(s, i, begin):
            j = i
        else:
            # We have matched the start of the span.
            j = self.match_span_helper(s, i + len(begin), end,
                no_escape, no_line_break, no_word_break=no_word_break)
            # g.trace('** helper returns',j,len(s))
            if j == -1:
                j = i # A real failure.
            else:
                # A hack to handle continued strings. Should work for most languages.
                # Prepend "dots" to the kind, as a flag to setTag.
                dots = j > len(s) and begin in "'\"" and end in "'\"" and kind.startswith('literal')
                if dots:
                    kind = 'dots'+kind
                    if trace: g.trace('underline', kind, repr(s[i:j]))
                # A match
                i2 = i + len(begin); j2 = j + len(end)
                if delegate:
                    self.colorRangeWithTag(s, i, i2, kind, delegate=None, exclude_match=exclude_match)
                    self.colorRangeWithTag(s, i2, j, kind, delegate=delegate, exclude_match=exclude_match)
                    self.colorRangeWithTag(s, j, j2, kind, delegate=None, exclude_match=exclude_match)
                else:
                    self.colorRangeWithTag(s, i, j2, kind, delegate=None, exclude_match=exclude_match)
                j = j2
                self.prev = (i, j, kind)
        self.trace_match(kind, s, i, j)
        # New in Leo 5.5: don't recolor everything after continued strings.
        if j > len(s) and not dots:
            j = len(s) + 1

            def span(s):
                # Note: bindings are frozen by this def.
                return self.restart_match_span(s,
                    # Positional args, in alpha order
                    delegate, end, exclude_match, kind,
                    no_escape, no_line_break, no_word_break)

            self.setRestart(span,
                # These must be keyword args.
                delegate=delegate, end=end,
                exclude_match=exclude_match,
                kind=kind,
                no_escape=no_escape,
                no_line_break=no_line_break,
                no_word_break=no_word_break)
            if trace: g.trace('***Continuing', kind, i, j, len(s), s[i: j])
        elif j != i:
            if trace: g.trace('***Ending', kind, i, j, s[i: j])
            self.clearState()
        return j - i # Correct, whatever j is.
    #@+node:ekr.20110605121601.18623: *5* jedit.match_span_helper
    def match_span_helper(self, s, i, pattern, no_escape, no_line_break, no_word_break):
        '''
        Return n >= 0 if s[i] ends with a non-escaped 'end' string.
        '''
        esc = self.escape
        while 1:
            j = s.find(pattern, i)
            # g.trace(no_line_break,j,len(s))
            if j == -1:
                # Match to end of text if not found and no_line_break is False
                if no_line_break:
                    return -1
                else:
                    return len(s) + 1
            elif no_word_break and j > 0 and s[j - 1] in self.word_chars:
                return -1 # New in Leo 4.5.
            elif no_line_break and '\n' in s[i: j]:
                return -1
            elif esc and not no_escape:
                # Only an odd number of escapes is a 'real' escape.
                escapes = 0; k = 1
                while j - k >= 0 and s[j - k] == esc:
                    escapes += 1; k += 1
                if (escapes % 2) == 1:
                    assert s[j - 1] == esc
                    i += 1 # 2013/08/26: just advance past the *one* escaped character.
                    # g.trace('escapes',escapes,repr(s[i:]))
                else:
                    return j
            else:
                return j
    #@+node:ekr.20110605121601.18624: *5* jedit.restart_match_span
    def restart_match_span(self, s,
        delegate, end, exclude_match, kind,
        no_escape, no_line_break, no_word_break
    ):
        '''Remain in this state until 'end' is seen.'''
        trace = False and not g.unitTesting
        i = 0
        j = self.match_span_helper(s, i, end, no_escape, no_line_break, no_word_break)
        if j == -1:
            j2 = len(s) + 1
        elif j > len(s):
            j2 = j
        else:
            j2 = j + len(end)
        if delegate:
            self.colorRangeWithTag(s, i, j, kind,
                delegate=delegate, exclude_match=exclude_match)
            self.colorRangeWithTag(s, j, j2, kind,
                delegate=None, exclude_match=exclude_match)
        else: # avoid having to merge ranges in addTagsToList.
            self.colorRangeWithTag(s, i, j2, kind,
                delegate=None, exclude_match=exclude_match)
        j = j2
        self.trace_match(kind, s, i, j)
        if j > len(s):

            def span(s):
                return self.restart_match_span(s,
                    # Positional args, in alpha order
                    delegate, end, exclude_match, kind,
                    no_escape, no_line_break, no_word_break)

            self.setRestart(span,
                # These must be keywords args.
                delegate=delegate, end=end, kind=kind,
                no_escape=no_escape,
                no_line_break=no_line_break,
                no_word_break=no_word_break)
            if trace: g.trace('***Re-continuing', i, j, len(s), s)
        else:
            if trace: g.trace('***ending', i, j, len(s), s)
            self.clearState()
        return j # Return the new i, *not* the length of the match.
    #@+node:ekr.20110605121601.18625: *4* jedit.match_span_regexp
    def match_span_regexp(self, s, i,
        kind='', begin='', end='',
        at_line_start=False, at_whitespace_end=False, at_word_start=False,
        delegate='', exclude_match=False,
        no_escape=False, no_line_break=False, no_word_break=False,
    ):
        '''Succeed if s[i:] starts with 'begin' (a regular expression) and
        contains a following 'end'.
        '''
        if self.verbose: g.trace('begin', repr(begin), 'end', repr(end), self.dump(s[i:]))
        if at_line_start and i != 0 and s[i - 1] != '\n': return 0
        if at_whitespace_end and i != g.skip_ws(s, 0): return 0
        if at_word_start and i > 0 and s[i - 1] in self.word_chars: return 0 # 7/5/2008
        if at_word_start and i + len(begin) + 1 < len(s) and s[i + len(begin)] in self.word_chars:
            return 0 # 7/5/2008
        n = self.match_regexp_helper(s, i, begin)
        # We may have to allow $n here, in which case we must use a regex object?
        if n > 0:
            j = i + n
            j2 = s.find(end, j)
            if j2 == -1: return 0
            if self.escape and not no_escape:
                # Only an odd number of escapes is a 'real' escape.
                escapes = 0; k = 1
                while j - k >= 0 and s[j - k] == self.escape:
                    escapes += 1; k += 1
                if (escapes % 2) == 1:
                    # An escaped end **aborts the entire match**:
                    # there is no way to 'restart' the regex.
                    return 0
            i2 = j2 - len(end)
            if delegate:
                self.colorRangeWithTag(s, i, j, kind, delegate=None, exclude_match=exclude_match)
                self.colorRangeWithTag(s, j, i2, kind, delegate=delegate, exclude_match=False)
                self.colorRangeWithTag(s, i2, j2, kind, delegate=None, exclude_match=exclude_match)
            else: # avoid having to merge ranges in addTagsToList.
                self.colorRangeWithTag(s, i, j2, kind, delegate=None, exclude_match=exclude_match)
            self.prev = (i, j, kind)
            self.trace_match(kind, s, i, j2)
            return j2 - i
        else: return 0
    #@+node:ekr.20110605121601.18626: *4* jedit.match_word_and_regexp
    def match_word_and_regexp(self, s, i,
        kind1='', word='',
        kind2='', pattern='',
        at_line_start=False, at_whitespace_end=False, at_word_start=False,
        exclude_match=False
    ):
        '''Succeed if s[i:] matches pattern.'''
        if not self.allow_mark_prev: return 0
        if (False or self.verbose): g.trace(i, repr(s[i: i + 20]))
        if at_line_start and i != 0 and s[i - 1] != '\n': return 0
        if at_whitespace_end and i != g.skip_ws(s, 0): return 0
        if at_word_start and i > 0 and s[i - 1] in self.word_chars: return 0
        if at_word_start and i + len(word) + 1 < len(s) and s[i + len(word)] in self.word_chars:
            j = i
        if not g.match(s, i, word):
            return 0
        j = i + len(word)
        n = self.match_regexp_helper(s, j, pattern)
        if n == 0:
            return 0
        self.colorRangeWithTag(s, i, j, kind1, exclude_match=exclude_match)
        k = j + n
        self.colorRangeWithTag(s, j, k, kind2, exclude_match=False)
        self.prev = (j, k, kind2)
        self.trace_match(kind1, s, i, j)
        self.trace_match(kind2, s, j, k)
        return k - i
    #@+node:ekr.20110605121601.18627: *4* jedit.skip_line
    def skip_line(self, s, i):
        if self.escape:
            escape = self.escape + '\n'
            n = len(escape)
            while i < len(s):
                j = g.skip_line(s, i)
                if not g.match(s, j - n, escape):
                    return j
                # g.trace('escape',s[i:j])
                i = j
            return i
        else:
            return g.skip_line(s, i)
                # Include the newline so we don't get a flash at the end of the line.
    #@+node:ekr.20110605121601.18628: *4* jedit.trace_match
    def trace_match(self, kind, s, i, j):
        if j != i and self.trace_match_flag:
            g.trace(kind, i, j, g.callers(2), self.dump(s[i: j]))
    #@+node:ekr.20110605121601.18629: *3*  jedit.State methods
    #@+node:ekr.20110605121601.18630: *4* jedit.clearState
    def clearState(self):
        '''
        Create a *language-specific* default state.
        This properly forces a full recoloring when @language changes.
        '''
        state = self.colorizer.language or 'no-language'
        state = state.replace('python','py').replace('markdown','md')
        n = self.stateNameToStateNumber(None, state)
        self.setState(n)
        return n
    #@+node:ekr.20110605121601.18631: *4* jedit.computeState
    def computeState(self, f, keys):
        '''Compute the state name associated with f and all the keys.

        Return a unique int n representing that state.'''
        # Abbreviate arg names.
        d = {
            'delegate': 'del',
            'end': 'end',
            'at_line_start': 'start',
            'at_whitespace_end': 'ws-end',
            'exclude_match': '!match',
            'no_escape': '!esc',
            'no_line_break': '!lbrk',
            'no_word_break': '!lbrk',
        }
        result = [self.colorizer.language]
        if not self.rulesetName.endswith('_main'):
            result.append(self.rulesetName)
        if f:
            result.append(f.__name__)
        for key in sorted(keys):
            keyVal = keys.get(key)
            val = d.get(key)
            if val is None:
                val = keys.get(key)
                result.append('%s=%s' % (key, val))
            elif keyVal is True:
                result.append('%s' % val)
            elif keyVal is False:
                pass
            elif keyVal not in (None, ''):
                result.append('%s=%s' % (key, keyVal))
        state = ';'.join(result).lower()
        table = (
            ('kind=', ''),
            ('literal', 'lit'),
            ('markdown', 'md'),
            ('python', 'py'),
            ('restart', '@'),
        )
        for pattern, s in table:
            state = state.replace(pattern, s)
        n = self.stateNameToStateNumber(f, state)
        return n
    #@+node:ekr.20110605121601.18632: *4* jedit.getters & setters
    def currentBlockNumber(self):
        block = self.highlighter.currentBlock()
        return block.blockNumber() if block and block.isValid() else -1

    def currentState(self):
        return self.highlighter.currentBlockState()

    def prevState(self):
        return self.highlighter.previousBlockState()

    def setState(self, n):
        self.highlighter.setCurrentBlockState(n)
    #@+node:ekr.20170125141148.1: *4* jedit.inColorState
    def inColorState(self):
        '''True if the *current* state is not disabed.'''
        n = self.currentState()
        state = self.stateDict.get(n, 'no-state')
        enabled = (
            not state.endswith('@nocolor') and
            not state.endswith('@nocolor-node') and
            not state.endswith('@killcolor'))
        # g.trace(enabled, state)
        return enabled

      
    #@+node:ekr.20110605121601.18633: *4* jedit.setRestart & setLanguage
    def setRestart(self, f, **keys):
        n = self.computeState(f, keys)
        self.setState(n)
        return n

    #@+node:ekr.20110605121601.18635: *4* jedit.showState & showCurrent/PrevState
    def showState(self, n):
        state = self.stateDict.get(n, 'no-state')
        return '%2s:%s' % (n, state)

    def showCurrentState(self):
        n = self.currentState()
        return self.showState(n)

    def showPrevState(self):
        n = self.prevState()
        return self.showState(n)
    #@+node:ekr.20110605121601.18636: *4* jedit.stateNameToStateNumber
    def stateNameToStateNumber(self, f, stateName):
        # stateDict:     Keys are state numbers, values state names.
        # stateNameDict: Keys are state names, values are state numbers.
        # restartDict:   Keys are state numbers, values are restart functions
        n = self.stateNameDict.get(stateName)
        if n is None:
            n = self.nextState
            self.stateNameDict[stateName] = n
            self.stateDict[n] = stateName
            self.restartDict[n] = f
            self.nextState += 1
            # g.trace('========',n,stateName)
        return n
    #@+node:ekr.20110605121601.18637: *3* jedit.colorRangeWithTag
    def colorRangeWithTag(self, s, i, j, tag, delegate='', exclude_match=False):
        '''Actually colorize the selected range.

        This is called whenever a pattern matcher succeed.'''
        trace = False and not g.unitTesting
            # A superb trace: enable this first to see what gets colored.
        if not self.inColorState():
            # Do *not* check x.flag here. It won't work.
            if trace: g.trace('not in color state')
            return
        if delegate:
            if trace:
                if len(repr(s[i: j])) <= 20:
                    s2 = repr(s[i: j])
                else:
                    s2 = repr(s[i: i + 17 - 2] + '...')
                g.trace('%25s %3s %3s %-20s %s' % (
                    ('%s.%s' % (delegate, tag)), i, j, s2, g.callers(2)))
            # self.setTag(tag,s,i,j) # 2011/05/31: Do the initial color.
            self.modeStack.append(self.modeBunch)
            self.init_mode(delegate)
            while 0 <= i < j and i < len(s):
                progress = i
                assert j >= 0, j
                for f in self.rulesDict.get(s[i], []):
                    n = f(self, s, i)
                    if n is None:
                        g.trace('Can not happen: delegate matcher returns None')
                    elif n > 0:
                        # if trace: g.trace('delegate',delegate,i,n,f.__name__,repr(s[i:i+n]))
                        i += n; break
                else:
                    # New in Leo 4.6: Use the default chars for everything else.
                    # New in Leo 4.8 devel: use the *delegate's* default characters if possible.
                    default_tag = self.attributesDict.get('default')
                    # g.trace(default_tag)
                    self.setTag(default_tag or tag, s, i, i + 1)
                    i += 1
                assert i > progress
            bunch = self.modeStack.pop()
            self.initModeFromBunch(bunch)
        elif not exclude_match:
            if trace:
                s2 = repr(s[i: j]) if len(repr(s[i: j])) <= 20 else repr(s[i: i + 17 - 2] + '...')
                g.trace('%25s %3s %3s %-20s %s' % (
                    ('%s.%s' % (self.language_name, tag)), i, j, s2, g.callers(2)))
            self.setTag(tag, s, i, j)
        if tag != 'url':
            # Allow URL's *everywhere*.
            j = min(j, len(s))
            while i < j:
                if s[i].lower() in 'fh': # file|ftp|http|https
                    n = self.match_any_url(s, i)
                    i += max(1, n)
                else:
                    i += 1
    #@+node:ekr.20110605121601.18638: *3* jedit.mainLoop
    def mainLoop(self, n, s):
        '''Colorize a *single* line s, starting in state n.'''
        f = self.restartDict.get(n)
        i = f(s) if f else 0
        # if trace: g.trace('===== %30s %r' % (self.showCurrentState(), s))
        while i < len(s):
            progress = i
            functions = self.rulesDict.get(s[i], [])
            # g.printList(functions)
            for f in functions:
                n = f(self, s, i)
                if n is None:
                    g.trace('Can not happen: n is None', repr(f))
                    break
                elif n > 0: # Success. The match has already been colored.
                    # if f.__name__ != 'match_blanks': g.trace(f.__name__, repr(s[i:i+n]))
                    i += n
                    break
                elif n < 0: # Total failure.
                    # g.trace('%s %r' % (f.__name__, s[i:i-n]))
                    i += -n
                    break
                else: # Partial failure: Do not break or change i!
                    pass 
            else:
                i += 1
            assert i > progress
        # Don't even *think* about changing state here.
        # if trace: g.trace('----- %30s %r' % (self.showCurrentState(), s))
    #@+node:ekr.20110605121601.18640: *3* jedit.recolor (entry, good trace)
    def recolor(self, s):
        '''
        jEdit.recolor: Recolor a *single* line, s.
        QSyntaxHighligher calls this method repeatedly and automatically.
        '''
        trace = False and not g.unitTesting
        self.recolorCount += 1
        # *Always* copy the state. mainLoop may change it.
        block_n = self.currentBlockNumber()
        n = self.prevState()
        if trace: g.trace('%25s %-5s %-3s %r' % (
            self.showState(n), self.colorizer.flag, block_n, s))
        if block_n == 0:
            self.defaultLanguage = self.colorizer.language
            if self.colorizer.flag and n == -1:
                n = self.clearState()
            elif not self.colorizer.flag:
                n = self.setRestart(self.restartNoColor)
        self.setState(n)
        # Always color the line, even if colorizing is disabled.
        if not s.isspace():
            self.mainLoop(n, s)
    #@+node:ekr.20110605121601.18641: *3* jedit.setTag
    def setTag(self, tag, s, i, j):
        '''Set the tag in the highlighter.'''
        trace = False and not g.unitTesting
        trace_all = True
        self.n_setTag += 1
        if i == j:
            if trace: g.trace('empty range')
            return
        if trace and trace_all:
            g.trace('%7s %s' % (tag, s[i:j]))
        wrapper = self.wrapper # A QTextEditWrapper
        tag = tag.lower() # 2011/10/28
        # A hack to allow continuation dots on any tag.
        dots = tag.startswith('dots')
        if dots:
            tag = tag[len('dots'):]
            if trace: g.trace('dotted tag:', tag)
        colorName = wrapper.configDict.get(tag)
        # Munge the color name.
        if not colorName:
            if trace: g.trace('no color for %s' % tag)
            return
        if colorName[-1].isdigit() and colorName[0] != '#':
            colorName = colorName[: -1]
        # Get the actual color.
        color = self.actualColorDict.get(colorName)
        if not color:
            color = QtGui.QColor(colorName)
            if color.isValid():
                self.actualColorDict[colorName] = color
            else:
                return g.trace('unknown color name', colorName, g.callers())
        underline = wrapper.configUnderlineDict.get(tag)
        format = QtGui.QTextCharFormat()
        font = self.fonts.get(tag)
        if font:
            format.setFont(font)
        if trace:
            g.trace(
                '===== %3s %3s %3s %9s %7s' % (
                    i, j, len(s), font and id(font) or '<no font>', colorName),
                '%-10s %-25s' % (tag, s[i: j]))
        if tag in ('blank', 'tab'):
            if tag == 'tab' or colorName == 'black':
                format.setFontUnderline(True)
            if colorName != 'black':
                format.setBackground(color)
        elif underline:
            format.setForeground(color)
            format.setUnderlineStyle(format.SingleUnderline)
            format.setFontUnderline(True)
        elif dots:
            format.setForeground(color)
            format.setUnderlineStyle(format.DotLine)
        else:
            format.setForeground(color)
            format.setUnderlineStyle(format.NoUnderline)
        self.tagCount += 1
        self.highlighter.setFormat(i, j - i, format)
    #@-others
#@+node:ekr.20110605121601.18551: ** class LeoQtColorizer
# This is c.frame.body.colorizer

class LeoQtColorizer(object):
    '''An adaptor class that interfaces Leo's core to the colorizer.
    
    The interface consists of:

    1. a subclass of QSyntaxHighlighter,

    2. the JEditColorizer class that contains the
       pattern-matchin code from the threading colorizer plugin.
       '''
    #@+others
    #@+node:ekr.20110605121601.18552: *3*  colorizer.ctor
    def __init__(self, c, widget):
        '''Ctor for LeoQtColorizer class.'''
        # g.trace('(LeoQtColorizer)',widget)
        self.c = c
        self.widget = widget
        # Step 1: create the ivars.
        self.count = 0 # For unit testing.
        self.colorCacheFlag = False
        self.enabled = c.config.getBool('use_syntax_coloring')
        self.error = False # Set if there is an error in jeditColorizer.recolor
        self.flag = True # Per-node enable/disable flag.
        self.full_recolor_count = 0 # For unit testing.
        self.killColorFlag = False
        self.language = 'python' # set by scanColorDirectives.
        self.languageList = [] # List of color directives in the node the determines it.
        # self.max_chars_to_colorize = c.config.getInt('qt_max_colorized_chars') or 0
            # No longer needed now that coloring is continued in the background.
        self.oldLanguageList = []
        self.oldV = None
        self.showInvisibles = False
        # Step 2: create the highlighter.
        self.highlighter = None
        self.colorer = None
             # No colorer for Scintilla
        if isinstance(widget, QtWidgets.QTextEdit):
            self.highlighter = LeoHighlighter(c, 
                colorizer = self,
                document = widget.document(),
            )
            assert self.colorer # Now done in LeoHighlighter.ctor.
        widget.leo_colorizer = self
        # Step 3: finish enabling.
        if self.enabled:
            self.enabled = hasattr(self.highlighter, 'currentBlock')
    #@+node:ekr.20110605121601.18553: *3* colorizer.colorize & helper
    def colorize(self, p, incremental=False, interruptable=True):
        '''
        Python 2: This is the main LeoQtColorizer entry point.
                  leo_h.rehighlight *is* called.
        Python 3: LeoQtColorizer.init does all the work(!)
                  leo_h.rehighlight is never called(!)
        '''
        # This method is called only with Python 2.
        trace = False and not g.unitTesting
        verbose = True
        c = self.c
        self.count += 1 # For unit testing.
        if not incremental:
            self.full_recolor_count += 1
        s = p.b
        if not s.strip():
            if trace: g.trace('no body', p.h)
            self.kill()
            return
        if s.startswith('@killcolor'):
            if trace: g.trace('@killcolor')
            self.kill()
            return
        elif self.enabled:
            oldFlag = self.flag
            self.updateSyntaxColorer(p)
                # sets self.flag and self.language and self.languageList.
            if trace and verbose:
                g.trace('old: %s, new: %s, %s' % (
                    self.oldLanguageList, self.languageList, repr(p.h)))
            # fullRecolor is True if we can not do an incremental recolor.
            fullRecolor = (
                oldFlag != self.flag or
                self.oldV != p.v or
                self.oldLanguageList != self.languageList or
                not incremental
            )
            # 2012/03/09: Determine the present language from the insertion
            # point if there are more than one @language directives in effect
            # and we are about to do an incremental recolor.
            if len(self.languageList) > 0 and not fullRecolor:
                language = self.scanColorByPosition(p) # May reset self.language
                if language != self.colorer.language_name:
                    if trace: g.trace('** must rescan', self.c.frame.title, language)
                    fullRecolor = True
                    self.language = language
            if fullRecolor:
                if trace: g.trace(
                    '** calling rehighlight',
                    self.highlighter, g.callers())
                self.oldLanguageList = self.languageList[:]
                self.oldV = p.v
                if trace: g.trace(p and p.h)
                # Do NOT call rehighlight here.
                # That causes a *huge* slowdown.
                doc = c.frame.body.widget.document()
                doc.markContentsDirty(0, len(p.b))
        return "ok" # For unit testing.
    #@+node:ekr.20120309075544.9888: *4* scanColorByPosition (LeoQtColorizer)
    def scanColorByPosition(self, p):
        c = self.c
        wrapper = c.frame.body.wrapper
        i = wrapper.getInsertPoint()
        s = wrapper.getAllText()
        i1, i2 = g.getLine(s, i)
        tag = '@language'
        language = self.language
        for s in g.splitLines(s[: i1]):
            if s.startswith(tag):
                language = s[len(tag):].strip()
        return language
    #@+node:ekr.20110605121601.18554: *3* colorizer.enable/disable (not used)
    def disable(self, p):
        g.trace(g.callers(4))
        if self.enabled:
            self.flag = False
            self.enabled = False
            self.highlighter.rehighlight(p) # Do a full recolor (to black)

    def enable(self, p):
        g.trace(g.callers(4))
        if not self.enabled:
            self.enabled = True
            self.flag = True
            # Do a full recolor, but only if we aren't changing nodes.
            if self.c.currentPosition() == p:
                self.highlighter.rehighlight(p)
    #@+node:ekr.20170115041807.1: *3* colorizer.init (new)
    def init (self, p, s):
        '''Init the colorizer using p, p's ancestors and s instead of p.b.'''
        # g.trace('(colorizer)', p and p.h)
        if p:
            self.updateSyntaxColorer(p)
                # Must be called before colorer.init().
            self.colorer.init(p, s)
    #@+node:ekr.20140827112712.18468: *3* colorizer.kill (to be deleted)
    def kill(self): # c.frame.body.colorizer.kill
        '''Kill any queue colorizing.'''
        if self.highlighter and hasattr(self.highlighter, 'kill'):
            self.highlighter.kill()
    #@+node:ekr.20110605121601.18562: *3* colorizer.updateSyntaxColorer & helpers
    def updateSyntaxColorer(self, p):
        '''Scan for color directives in p and its ancestors.'''
        trace = False and not g.unitTesting
        # An important hack: shortcut everything if the first line is @killcolor.
        if False and p.b.startswith('@killcolor'):
            if trace: g.trace('@killcolor')
            self.flag = False
            return self.flag
        else:
            # self.flag is True unless an unambiguous @nocolor is seen.
            p = p.copy()
            self.flag = self.useSyntaxColoring(p)
            self.scanColorDirectives(p) # Sets self.language
        if trace: g.trace(self.flag, self.language, p.h)
        return self.flag
    #@+node:ekr.20110605121601.18556: *4* scanColorDirectives (LeoQtColorizer) & helper
    def scanColorDirectives(self, p):
        '''Set self.language based on the directives in p's tree.'''
        trace = False and not g.unitTesting
        c = self.c
        if c is None: return None # self.c may be None for testing.
        root = p.copy()
        self.colorCacheFlag = False
        self.language = None
        self.rootMode = None # None, "code" or "doc"
        for p in root.self_and_parents():
            theDict = g.get_directives_dict(p)
            # if trace: g.trace(p.h,theDict)
            #@+<< Test for @colorcache >>
            #@+node:ekr.20121003152523.10126: *5* << Test for @colorcache >>
            # The @colorcache directive is a per-node directive.
            if p == root:
                self.colorCacheFlag = 'colorcache' in theDict
                # g.trace('colorCacheFlag: %s' % self.colorCacheFlag)
            #@-<< Test for @colorcache >>
            #@+<< Test for @language >>
            #@+node:ekr.20110605121601.18557: *5* << Test for @language >>
            if 'language' in theDict:
                s = theDict["language"]
                aList = self.findLanguageDirectives(p)
                # In the root node, we use the first (valid) @language directive,
                # no matter how many @language directives the root node contains.
                # In ancestor nodes, only unambiguous @language directives
                # set self.language.
                if p == root or len(aList) == 1:
                    self.languageList = list(set(aList))
                    self.language = aList and aList[0] or []
                    break
            #@-<< Test for @language >>
            #@+<< Test for @root, @root-doc or @root-code >>
            #@+node:ekr.20110605121601.18558: *5* << Test for @root, @root-doc or @root-code >>
            if 'root' in theDict and not self.rootMode:
                s = theDict["root"]
                if g.match_word(s, 0, "@root-code"):
                    self.rootMode = "code"
                elif g.match_word(s, 0, "@root-doc"):
                    self.rootMode = "doc"
                else:
                    doc = c.config.at_root_bodies_start_in_doc_mode
                    self.rootMode = "doc" if doc else "code"
            #@-<< Test for @root, @root-doc or @root-code >>
        # 2011/05/28: If no language, get the language from any @<file> node.
        if self.language:
            if trace: g.trace('found @language %s %s' % (self.language, self.languageList))
            return self.language
        #  Attempt to get the language from the nearest enclosing @<file> node.
        self.language = g.getLanguageFromAncestorAtFileNode(root)
        if not self.language:
            if trace: g.trace('using default', c.target_language)
            self.language = c.target_language
        return self.language # For use by external routines.
    #@+node:ekr.20110605121601.18559: *5* findLanguageDirectives
    def findLanguageDirectives(self, p):
        '''Scan p's body text for *valid* @language directives.

        Return a list of languages.'''
        # Speed not very important: called only for nodes containing @language directives.
        trace = False and not g.unitTesting
        aList = []
        for s in g.splitLines(p.b):
            if g.match_word(s, 0, '@language'):
                i = len('@language')
                i = g.skip_ws(s, i)
                j = g.skip_id(s, i)
                if j > i:
                    word = s[i: j]
                    if self.isValidLanguage(word):
                        aList.append(word)
                    else:
                        if trace: g.trace('invalid', word)
        if trace: g.trace(aList)
        return aList
    #@+node:ekr.20110605121601.18560: *5* isValidLanguage
    def isValidLanguage(self, language):
        fn = g.os_path_join(g.app.loadDir, '..', 'modes', '%s.py' % (language))
        return g.os_path_exists(fn)
    #@+node:ekr.20110605121601.18563: *4* colorizer.useSyntaxColoring & helper
    def useSyntaxColoring(self, p):
        """Return True unless p is unambiguously under the control of @nocolor."""
        trace = False and not g.unitTesting
        if not p:
            if trace: g.trace('no p', repr(p))
            return False
        p = p.copy()
        first = True; kind = None; val = True
        self.killColorFlag = False
        ### for p in p.self_and_parents():
        for p in p.parents():
            d = self.findColorDirectives(p)
            color, no_color = 'color' in d, 'nocolor' in d
            # An @nocolor-node in the first node disabled coloring.
            if first and 'nocolor-node' in d:
                kind = '@nocolor-node'
                self.killColorFlag = True
                val = False; break
            # A killcolor anywhere disables coloring.
            elif 'killcolor' in d:
                kind = '@killcolor %s' % p.h
                self.killColorFlag = True
                val = False; break
            # A color anywhere in the target enables coloring.
            elif color and first:
                kind = 'color %s' % p.h
                val = True; break
            # Otherwise, the @nocolor specification must be unambiguous.
            elif no_color and not color:
                kind = '@nocolor %s' % p.h
                val = False; break
            elif color and not no_color:
                kind = '@color %s' % p.h
                val = True; break
            first = False
        if trace: g.trace(val, kind)
        return val
    #@+node:ekr.20110605121601.18564: *5* findColorDirectives
    color_directives_pat = re.compile(
        # Order is important: put longest matches first.
        r'(^@color|^@killcolor|^@nocolor-node|^@nocolor)'
        , re.MULTILINE)

    def findColorDirectives(self, p):
        '''Scan p for @color, @killcolor, @nocolor and @nocolor-node directives.

        Return a dict containing pointers to the start of each directive.'''
        trace = False and not g.unitTesting
        d = {}
        anIter = self.color_directives_pat.finditer(p.b)
        for m in anIter:
            # Remove leading '@' for compatibility with
            # functions in leoGlobals.py.
            word = m.group(0)[1:]
            d[word] = word
        if trace: g.trace(d)
        return d
    #@-others
#@+node:ekr.20110605121601.18565: ** class LeoHighlighter
# This is c.frame.body.colorizer.highlighter
# Careful: we may be running from the bridge.
if QtGui:

    class LeoHighlighter(QtGui.QSyntaxHighlighter):
        '''A subclass of QSyntaxHighlighter that overrides
        the highlightBlock and rehighlight methods.

        All actual syntax coloring is done in the jeditColorer class.'''
        #@+others
        #@+node:ekr.20110605121601.18566: *3* leo_h.ctor
        def __init__(self, c, colorizer, document):
            '''ctor for LeoHighlighter class.'''
            self.c = c
            self.n_calls = 0
            assert isinstance(document, QtGui.QTextDocument), document
            # Init the base class.
            self.colorizer = colorizer
            self.colorer = JEditColorizer(c,
                colorizer=colorizer,
                highlighter=self,
                wrapper=c.frame.body.wrapper)
            colorizer.colorer = self.colorer
            QtGui.QSyntaxHighlighter.__init__(self, document)
                # Init the base class.
        #@+node:ekr.20110605121601.18568: *3* leo_h.rehighlight
        no_method_message = True # True: give message once.

        def rehighlight(self, p):
            '''
            Override base rehighlight method.
            Does nothing unless QSyntaxHighlighter.currentBlock exists.
            
            It appears that this method is seldom (never?) called!
            '''
            # pylint: disable=arguments-differ
            trace = True # and not g.unitTesting
            if trace: g.trace('=====', p and p.h, g.callers())
            if not hasattr(self, 'currentBlock'):
                if self.no_method_message:
                    self.no_method_message = False
                    g.trace('===== QSyntaxHighlighter has no currentBlock method')
                return
            c = self.c
            if not p.b.strip():
                if trace: g.trace('no body', p and p.h)
                return
            self.n_calls = 0
            tree = c.frame.tree
            self.widget = c.frame.body.widget
            if trace:
                t1 = time.clock()
            # n = self.colorer.recolorCount
            if self.colorizer.enabled:
                # Lock out onTextChanged.
                old_selecting = tree.selecting
                try:
                    tree.selecting = True
                    self.colorer.init(p, p.b)
                    QtGui.QSyntaxHighlighter.rehighlight(self)
                        # Execute the base class method.
                finally:
                    tree.selecting = old_selecting
            if trace:
                delta_t = time.clock()-t1
                g.trace('(leo_h) ----- %2.3f sec' % (delta_t), self.n_calls)
        #@+node:ekr.20110605121601.18567: *3* leo_h.highlightBlock
        def highlightBlock(self, s):
            """ Called by QSyntaxHiglighter """
            self.n_calls += 1
            if not self.colorizer.killColorFlag:
                s = g.toUnicode(s)
                self.colorer.recolor(s)
                    # Highlight just one line.
        #@-others
#@+node:ekr.20140906095826.18717: ** class NullScintillaLexer
if Qsci:

    class NullScintillaLexer(Qsci.QsciLexerCustom):
        '''A do-nothing colorizer for Scintilla.'''

        def __init__(self, c, parent=None):
            Qsci.QsciLexerCustom.__init__(self, parent)
                # Init the pase class
            self.leo_c = c
            self.configure_lexer()

        def description(self, style):
            return 'NullScintillaLexer'

        def setStyling(self, length, style):
            g.trace('(NullScintillaLexer)', length, style)

        def styleText(self, start, end):
            '''Style the text from start to end.'''
            # g.trace('(NullScintillaLexer)',start,end)

        def configure_lexer(self):
            '''Configure the QScintilla lexer.'''
            # c = self.leo_c
            lexer = self
            # To do: use c.config setting.
            # pylint: disable=no-member
            font = QtGui.QFont("DejaVu Sans Mono", 14)
            lexer.setFont(font)
#@+node:ekr.20140906081909.18689: ** class QScintillaColorizer(ColorizerMixin)
# This is c.frame.body.colorizer
class QScintillaColorizer(ColorizerMixin):
    '''A colorizer for a QsciScintilla widget.'''
    #@+others
    #@+node:ekr.20140906081909.18709: *3* qsc.ctor
    def __init__(self, c, widget):
        '''Ctor for QScintillaColorizer. widget is a '''
        # g.trace('QScintillaColorizer)',widget)
        ColorizerMixin.__init__(self, c)
            # init the base class.
        self.count = 0 # For unit testing.
        self.colorCacheFlag = False
        self.enabled = c.config.getBool('use_syntax_coloring')
        self.error = False # Set if there is an error in jeditColorizer.recolor
        self.flag = True # Per-node enable/disable flag.
        self.full_recolor_count = 0 # For unit testing.
        self.language = 'python' # set by scanColorDirectives.
        self.languageList = [] # List of color directives in the node the determines it.
        self.lexer = None # Set in changeLexer.
        self.oldLanguageList = []
        self.showInvisibles = False
        widget.leo_colorizer = self
        # Define/configure various lexers.
        if Qsci:
            self.lexersDict = {
                'python': Qsci.QsciLexerPython(parent=c.frame.body.wrapper.widget),
                # 'python': PythonLexer(parent=c.frame.body.wrapper.widget),
            }
            self.nullLexer = NullScintillaLexer(c)
        else:
            self.lexersDict = {}
            self.nullLexer = None
        lexer = self.lexersDict.get('python')
        self.configure_lexer(lexer)
    #@+node:ekr.20140906081909.18718: *3* qsc.changeLexer
    def changeLexer(self, language):
        '''Set the lexer for the given language.'''
        c = self.c
        wrapper = c.frame.body.wrapper
        w = wrapper.widget # A Qsci.QsciSintilla object.
        self.lexer = self.lexersDict.get(language, self.nullLexer)
        w.setLexer(self.lexer)
        # g.trace(language,self.lexer)
    #@+node:ekr.20140906095826.18721: *3* qsc.configure_lexer
    def configure_lexer(self, lexer):
        '''Configure the QScintilla lexer.'''
        # return # Try to use  USERPROFILE:SciTEUser.properties

        def oops(s):
            g.trace('bad @data qt-scintilla-styles:', s)
        # A small font size, to be magnified.

        c = self.c
        qcolor, qfont = QtGui.QColor, QtGui.QFont
        # font = qfont("Courier New",8,qfont.Bold)
        font = qfont("DejaVu Sans Mono", 14)
        lexer.setFont(font)
        lexer.setEolFill(False, -1)
        lexer.setStringsOverNewlineAllowed(False)
        table = None
        aList = c.config.getData('qt-scintilla-styles')
        if aList:
            aList = [s.split(',') for s in aList]
            table = []
            for z in aList:
                if len(z) == 2:
                    color, style = z
                    table.append((color.strip(), style.strip()),)
                else: oops('entry: %s' % z)
            # g.trace('@data ** qt-scintilla-styles',table)
        if not table:
            # g.trace('using default color table')
            black = '#000000'
            leo_green = '#00aa00'
            # See http://pyqt.sourceforge.net/Docs/QScintilla2/classQsciLexerPython.html
            # for list of selector names.
            table = (
                # EKR's personal settings: they are reasonable defaults.
                (black, 'ClassName'),
                ('#CD2626', 'Comment'), # Firebrick3
                (leo_green, 'Decorator'),
                (leo_green, 'DoubleQuotedString'),
                (black, 'FunctionMethodName'),
                ('blue', 'Keyword'),
                (black, 'Number'),
                (leo_green, 'SingleQuotedString'), # Leo green.
                (leo_green, 'TripleSingleQuotedString'),
                (leo_green, 'TripleDoubleQuotedString'),
                (leo_green, 'UnclosedString'),
                # End of line where string is not closed
                # style.python.13=fore:#000000,$(font.monospace),back:#E0C0E0,eolfilled
            )
        for color, style in table:
            if hasattr(lexer, style):
                style_number = getattr(lexer, style)
                try:
                    # g.trace(color,style)
                    lexer.setColor(qcolor(color), style_number)
                except Exception:
                    oops('bad color: %s' % color)
            else: oops('bad style name: %s' % style)
    #@+node:ekr.20140906081909.18707: *3* qsc.colorize (revise)
    def colorize(self, p, incremental=False, interruptable=True):
        '''The main Scintilla colorizer entry point.'''
        trace = False and not g.unitTesting
        self.count += 1 # For unit testing.
        if not incremental:
            self.full_recolor_count += 1
        if p.b.startswith('@killcolor'):
            if trace: g.trace('kill: @killcolor')
            self.kill()
        else:
            self.updateSyntaxColorer(p)
                # sets self.flag and self.language and self.languageList.
            if trace: g.trace(self.language)
            self.changeLexer(self.language)
        return "ok" # For unit testing.
    #@+node:ekr.20140906081909.18716: *3* qsc.kill
    def kill(self):
        '''Kill coloring for this node.'''
        self.changeLexer(language=None)
    #@-others
#@+node:ekr.20140906143232.18697: ** class PythonLexer (does not work)
# Stuck: regardless of class: there seems to be no way to force a recolor.
if Qsci:

    class PythonLexer(Qsci.QsciLexerCustom):
        '''A subclass of the Python lexer that colorizers section references.'''

        def __init__(self, parent=None):
            '''Ctor for PythonLexer class.'''
            Qsci.QsciLexerCustom.__init__(self, parent)
                # Init the base class.
            self.lexer = None
            self.parent = parent
            self.tag = '(PythonLexer)'

        def setStringsOverNewlineAllowed(self, aBool):
            pass

        def description(self, style):
            return self.tag

        def setStyling(self, length, style):
            g.trace(self.tag, length, style)

        def styleText(self, start, end):
            '''Style the text from start to end.'''
            g.trace(self.tag, start, end)
            self.lexer = Qsci.QsciLexerPython(parent=self.parent)
            self.lexer.setStringsOverNewlineAllowed(True)
            # self.lexer.styleText(start,end)

        def configure_lexer(self):
            '''Configure the QScintilla lexer.'''
            lexer = self
            # To do: use c.config setting.
            # pylint: disable=no-member
            font = QtGui.QFont("DejaVu Sans Mono", 14)
            lexer.setFont(font)
#@-others
#@@language python
#@@tabwidth -4
#@@pagewidth 70
#@-leo
