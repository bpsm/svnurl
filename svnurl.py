#!/usr/bin/env python

# SVNURL - A script to make working with svn urls easier.
# Copyright (c) 2008 Ben Smith-Mannschott
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import os
import os.path
import re
import sys
import getopt

def usage():
    print """
svnurl [--url | -u] [DIR]
  svn URL corresponding to given working directory

svnurl --branch NAME [DIR]
svnurl  -b      NAME [DIR]
  svn URL for branch NAME of given working directory or URL.

svnurl --tag NAME [DIR]
svnurl  -t   NAME [DIR]
  svn URL for tag NAME of given working directory or URL.

svnurl --trunk [--url | --name] [DIR]
svnurl  -T      [-u   |  -n]    [DIR]
  svn URL of trunk for project correspdonding to given directory or
  URL. Just the name of the trunk directory (TRUNK or trunk) if option
  --name is given.

svnurl -branch --ls [--url | --name] [DIR]
svnurl -b       -l   [-u   |  -n]    [DIR]
  list branches for the given working copy directory or URL.
  If --verbose, then list full URLs.

svnurl --tag  --ls [--url | --name] [DIR]
svnurl  -t     -l   [-u   |  -n]    [DIR]
  list tags for the given working copy directory or URL.
  If --verbose, then list full URLs.

svnurl --project [--url | --name] [DIR]
svnurl  -p        [-u   |  -n]   [DIR]
  print name or url (with option --url) of project corresponding to
  given working copy or URL.

svnurl --branch --dir [--url | --name] [DIR]
svnurl  -b       -d    [-u   |  -n]    [DIR]
  print url of branches directory corresponding to given URL or
  working directory.  Print only name if --name is provided.

svnurl --tag --dir [--url | --name] [DIR]
svnurl  -t    -d    [-u   |  -n]    [DIR]
  print url of tags directory corresponding to given URL or working
  directory. Print only name if --name is provided.

svnurl --root|-r [ --url | --name ] [DIR]
  branch/tag/trunk name or url corresponding to given working copy or
  URL.

svnurl --project --all [ --url | --name ] [DIR]
svnurl  -p        -a   [  -u   |  -n    ] [DIR]
  List the urls (or names) of all projects in the designated
  repository.
"""

class SvnURL(object):
    svn_url_pat = re.compile(r"^(svn([+]ssh)?|http[s]?|file)://.*$")
    pat=re.compile(r"""([^ ]+)/([^ /]+)/
                    (TRUNK|BRANCHES|TAGS|trunk|branches|tags|Trunk|Branches|Tags)
                    (/([^ ]*))?$""", re.X)
    def __init__(self, url):
        if not SvnURL.svn_url_pat.match(url):
            u = url_for_wd(url) or url_for_wd(os.path.expanduser(url))
            assert u is not None, \
                "%s doesn't look like an svn url or working copy" % (url,)
            url = u
        url = normalize(str(url))
        self.whole_url = url
        m = SvnURL.pat.match(url)
        if m:
            self.project_name = m.group(2)
            self.project_root_url = m.group(1) + "/" + m.group(2)
            self.branch_kind = m.group(3).lower()
            self.lowercase = (m.group(3) == self.branch_kind)
            self.titlecase = (m.group(3) == self.branch_kind.title())
            self.branch_container_url = m.group(1) + "/" + m.group(2) + "/" + m.group(3)
            if self.branch_kind == "trunk":
                self.branch_name = None
            else:
                g = m.group(5)
                if g:
                    self.branch_name = g.split("/")[0]
                else:
                    self.branch_name = None

            self.branch_root_url = self.branch_container_url
            if self.branch_name:
                self.branch_root_url += ("/" + self.branch_name)
            self.online = False
        else:
            self.project_name = url.split("/")[-1]
            self.project_root_url = self.whole_url

            self.branch_kind = None
            self.lowercase = True
            self.titlecase = False
            for line in svn_lsdirs(self.project_root_url):
                if line in ("TRUNK", "BRANCHES", "TAGS"):              
                    self.titlecase = False
                    self.lowercase = False
                elif line in ("Trunk", "Branches", "Tags"):
                    self.titlecase = True
                    self.lowercase = False
            self.online = True
            self.branch_container_url = None
            self.branch_root_url = None
            self.branch_name = None

        self.branch_base = self.__base("branches")
        self.tag_base = self.__base("tags")
        self.trunk_base = self.__base("trunk")

    def correct_case(self, str):
        if self.lowercase:
            return str.lower()
        elif self.titlecase:
            return str.title()
        else:
            return str.upper()

    def __base(self, kind):
        assert kind in ("trunk", "tags", "branches")
        return self.project_root_url + "/" + self.correct_case(kind)

    def branch(self, name):
        return SvnURL(self.branch_base + "/" + name)

    def tag(self, name):
        return SvnURL(self.tag_base + "/" + name)

    def trunk(self):
        return SvnURL(self.trunk_base)

    def branch_names(self):
        return svn_lsdirs(self.branch_base)

    def tag_names(self):
        return svn_lsdirs(self.tag_base)

    def branch_urls(self):
        for name in self.branch_names():
            yield SvnURL(self.branch_base + "/" + name)

    def tag_urls(self):
        for name in self.tag_names():
            yield SvnURL(self.tag_base + "/" + name)

    def __str__(self):
        return self.whole_url

    def __repr__(self):
        return "SvnURL(%r)" % self.whole_url

    def __cmp__(self, other):
        c = cmp(type(self), type(other))
        if c == 0:
            return cmp(str(self), str(other))
        else:
            return c

svn_url_pat = re.compile(r"^(svn([+]ssh)?|http[s]?|file)://.*$")

def surl(url):
    if type(url) == SvnURL:
        return url
    else:
        return SvnURL(url)

def cmd(command, *args):
    commandline = " ".join([command] + [str(a) for a in args])
    for line in os.popen(commandline):
        yield line.rstrip()

def svn_ls(url):
    return cmd("svn", "ls", url)

def svn_lsdirs(url):
    return (line[:-1] for line in svn_ls(url) if line.endswith("/"))

def url_for_wd(wd="."):
    if os.path.isdir(os.path.join(wd, ".svn")):
        for x in cmd("svn", "info", wd):
            if x[:5] == "URL: ":
                return SvnURL(x[5:])
    return None

def normalize(url):
    if type(url) == SvnURL:
        return url
    while len(url) > 0 and url[-1] == "/":
        url = url[:-1]
    return url

def repo_root(url):
    assert url == normalize(url)
    prefix = "Repository Root: "
    for x in cmd("svn", "info", url):
        if x[:len(prefix)] == prefix:
            return x[len(prefix):]
    else:
        return None

def project_root(url):
    return surl(url).project_root_url

def branch_root(url):
    return surl(url).branch_root_url

def branch_name(url):
    return surl(url).branch_name

def tag_url(url, name):
    return surl(url).tag(name)

def trunk_url(url):
    return surl(url).trunk()

def branch_url(url, name):
    return surl(url).branch(name)


def do_branch_ls(flags, args):
    u = surl(args[0])
    if "url" in flags:
        assert "name" not in flags
        lines = u.branch_urls()
    else:
        lines = u.branch_names()
    print "\n".join(str(x) for x in lines)

def do_branch_dir(flags, args):
    u = surl(args[0])
    if "name" in flags:
        assert "url" not in flags
        print u.correct_case("branches")
    else:
        print u.branch_base

def do_branch_named(flags, args):
    print surl(args[1]).branch(args[0])

def do_tag_ls(flags, args):
    u = surl(args[0])
    if "url" in flags:
        assert "name" not in flags
        lines = u.tag_urls()
    else:
        lines = u.tag_names()
    print "\n".join(str(x) for x in lines)

def do_tag_dir(flags, args):
    u = surl(args[0])
    if "name" in flags:
        assert "url" not in flags
        print u.correct_case("tags")
    else:
        print u.tag_base

def do_tag_named(flags, args):
    print surl(args[1]).tag(args[0])

def do_trunk_dir(flags, args):
    u = surl(args[0])
    if "name" in flags:
        assert "url" not in flags
        print u.correct_case("trunk")
    else:
        print u.trunk_base


def do_project_dir(flags, args):
    u = surl(args[0])
    if "name" in flags:
        assert "url" not in flags
        print u.project_name
    else:
        print u.project_root_url

def do_project_all_dir(flags, args):
    containers = set(["TRUNK", "TAGS", "BRANCHES", "trunk", "tags", "branches", "Trunk", "Branches", "Tags"])
    def find_projects(url):
        dirs = set(svn_lsdirs(url))
        cnt = dirs.intersection(containers)
        if cnt:
            c = iter(cnt).next()
            yield surl(os.path.join(url, c))
        for d in dirs - containers:
            # TODO: be smart about URL encoding. In particular, spaces
            #       in "d" when joined to base url are a problem
            for p in find_projects(os.path.join(url, d)):
                yield p
    url = repo_root(surl(args[0]))
    for p in find_projects(url):
        if "name" in flags:
            print p.project_name
        else:
            print p.project_root_url

def do_current_dir(flags, args):
    u = surl(args[0])
    if "name" in flags:
        assert "url" not in flags
        print u.whole_url.split("/")[-1]
    else:
        print u.whole_url

def do_current_branchtag(flags, args):
    u = surl(args[0])
    if "name" in flags:
        assert "url" not in flags
        print u.branch_root_url.split("/")[-1]
    else:
        print u.branch_root_url

def main(argv):
    try:
        optlist, args = getopt.getopt(argv[1:],
                                      "btTpdunlar",
                                      ["branch", "tag", "trunk",
                                       "project", "dir", "url",
                                       "name", "ls", "list",
                                       "all", "root"])
        args += ["."]
    except getopt.GetoptError, e:
        print argv
        print e
        usage()
        sys.exit(2)

    flagnames = {"b": "branch",  "t": "tag",  "T": "trunk",
                 "p": "project", "d": "dir",  "u": "url",
                 "n": "name",    "l": "ls",   "a": "all",
                 "r": "root"}
    flags = set()
    for opt, parm in optlist:
        if opt[:2] == "--":
            if opt == "--list": opt = "--ls"
            flags.add(opt[2:])
        elif opt[:1] == "-":
            flags.add(flagnames[opt[1:]])

    if "branch" in flags:
        assert not flags.intersection(set(["tag", "trunk", "project", "root"]))
        if "ls" in flags:
            assert "dir" not in flags
            do_branch_ls(flags, args)
        elif "dir" in flags:
            assert "ls" not in flags
            do_branch_dir(flags, args)
        else:
            do_branch_named(flags, args)
    elif "tag" in flags:
        assert not flags.intersection(set(["branch", "trunk", "project", "root"]))
        if "ls" in flags:
            assert "dir" not in flags
            do_tag_ls(flags, args)
        elif "dir" in flags:
            assert "ls" not in flags
            do_tag_dir(flags, args)
        else:
            do_tag_named(flags, args)
    elif "trunk" in flags:
        assert not flags.intersection(set(["branch", "tag", "project", "root"]))
        do_trunk_dir(flags, args)

    elif "project" in flags:
        assert not flags.intersection(set(["branch", "tag", "trunk", "root"]))
        if "all" in flags:
            do_project_all_dir(flags, args)
        else:
            do_project_dir(flags, args)
    elif "root" in flags:
        assert not flags.intersection(set(["branch", "tag", "trunk", "project"]))
        do_current_branchtag(flags, args)
    else:
        do_current_dir(flags, args)

def test():
    os.chdir("/Users/bsmith/tmp/s.tag")
    main(["svnurl", "--url"])
    main(["svnurl", "--name"])
    main(["svnurl", "-u", "../s.branch"])
    main(["svnurl", "-n", "../s.trunk/Sources"])
    main(["svnurl", "-t", "tagname"])
    main(["svnurl", "-T"])
    main(["svnurl", "--branch", "branchname", "../s.branch"])
    main(["svnurl", "-b", "-l"])
    main(["svnurl", "-b", "-l", "-u"])
    main(["svnurl", "--tag", "--ls"])
    main(["svnurl", "-t", "--ls", "--url"])
    main(["svnurl", "-p", "../s.tag"])
    main(["svnurl", "-p", "../s.tag", "-u"])
    main(["svnurl", "-b", "-d", "--url"])
    main(["svnurl", "--branch", "--dir", "--name"])
    main(["svnurl", "--tag", "-d", "--url"])
    main(["svnurl", "-t", "--dir", "--name", "../s.branch"])


if __name__ == "__main__":
    main(sys.argv)
