#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2015 Fabrice Laporte - kray.me
# The MIT License http://www.opensource.org/licenses/mit-license.php

import argparse
import json
import os
import readline
import sys

from clint.textui import puts, colored
from difflib import SequenceMatcher



def prefilled_input(_prompt, prefill=''):
    if prefill:
        readline.set_startup_hook(lambda: readline.insert_text(prefill))
    readline.redisplay()
    try:
        return raw_input(_prompt)
    finally:
        readline.set_startup_hook()


class InputCompleter(object):  # Custom completer

    def __init__(self, options):
        self.options = sorted(options)

    def complete(self, text, state):
        if state == 0:
            if text:
                self.matches = [s for s in self.options
                                if s and s.startswith(text)]
            else:
                self.matches = self.options[:]
        try:
            return self.matches[state]
        except IndexError:
            return None


def find_category(categories, payee):
    for (c, keywords) in categories.items():
        if any([k.lower() in payee.lower() for k in keywords]):
            return c, k
    return None, None


def overwrite(text=''):
    #return text
    return '\x1b[1A\x1b[1M' + text


def diff(a, b, as_error=False):
    s = SequenceMatcher(None, a.lower(), b.lower())
    match = s.find_longest_match(0, len(a), 0, len(b))
    _, x, y = match
    return '%s%s%s' % (colored.red(b[:x]) if as_error else b[:x],
                       colored.green(b[x:x + y]),
                       colored.red(b[x + y:]) if as_error else b[x + y:])


def pick_category(default_cat, categories):
    COMPLETER = InputCompleter(categories.keys())
    readline.set_completer(COMPLETER.complete)
    category = raw_input('Category: ')
    if not category and default_cat:
        erase = raw_input(overwrite("Remove existing category [y,N]? ")) or 'N'
        if erase.upper() == 'N':
            category = default_cat
    readline.set_completer(None)
    return category


def pick_match(default_match, payee):
    while True:
        match = raw_input(overwrite("Match:"))
        if match not in payee:
                puts(overwrite('%s Match rejected...: %s\n') %
                     (colored.red('✖'), diff(payee, match, as_error=True)))
        else:
            puts(overwrite("%s Match: %s\n" % (colored.green('✔'),
                 str(match) if match else colored.red('<none>'))))
            break
    return match


def update_config(categories, prev_cat, prev_match, category, match, ):
    if category != prev_cat:
        categories[prev_cat].remove(prev_match)
        if not categories[prev_cat]:
            del categories[prev_cat]
        if category and match:
            if category not in categories:
                categories[category] = [match]
            else:
                categories.append(match)
    else:
        if match and match != prev_match:
            categories[category].remove(prev_match)
            categories[category].append(match)


def fetch_categories(lines, categories, options):
    readline.parse_and_bind('tab: complete')
    result = []
    for line in lines:
        if line.startswith('T'):
            amount = line[1:].strip()
        payee = line[1:].strip() if line.startswith('P') else None
        if payee:  # write payee line and find category to write on next line
            result.append(line)
            prev_cat, prev_match = find_category(categories, payee)
            category = prev_cat
            match = prev_match
            puts('Amount..: %s' % (colored.green(amount) if float(amount) > 0
                 else colored.red(amount)))
            puts('Payee...: %s' % (diff(prev_match, payee) if prev_match
                 else payee))
            puts("Category: %s" % prev_cat)
            edit = None
            if options['audit']:
                edit = raw_input('Edit [y/N]? ') or 'N'
            if not prev_cat or (edit.upper() == 'Y'):
                category = pick_category(prev_cat, categories)
                puts(overwrite('Category: %s\n') % (category if category else
                     colored.red('<none>')))
            if not prev_match or edit.upper() == 'Y' and category:
                match = pick_match(prev_match, payee)
            update_config(categories, prev_cat, prev_match, category, match)
            result.append('L%s\n' % category)
        elif not line.startswith('L'):  # overwrite previous categories
            result.append(line)
        if line.startswith('^'):
            if options['audit']:
                print(overwrite('Category: %s' % (category)))
            print '---'
    return result, categories


def main(argv=None):
    if argv is None:
        argv = sys.argv

    parser = argparse.ArgumentParser(
        description='Enrich your .QIF files with categories. '
        'See https://github.com/Kraymer/qifhack for more infos.')
    parser.add_argument('src', metavar='QIF_FILE',
                        help='.QIF file to process', default='')
    parser.add_argument('-a', '--audit-mode', dest='audit',
                        action='store_true', help=('pause after'
                                                   'each transaction'))
    parser.add_argument('-o', '--output', dest='dest',
                        help='Output filename. '
                        'DEFAULT: edit input file in-place', default='')
    parser.add_argument('-c', '--config', dest='config',
                        help='Configuration filename in json format. '
                        'DEFAULT: ~/.qifhack.json',
                        default=os.path.join(os.path.expanduser('~'),
                                             '.qifhack.json'))
    args = vars(parser.parse_args())
    if not args['dest']:
        args['dest'] = args['src']

    if os.path.isfile(args['config']):
        with open(args['config'], 'r') as cfg:
            cfg_dict = json.load(cfg)
    else:
        cfg_dict = {}
    with open(args['src'], 'r') as f:
        lines = f.readlines()
        result, categories = fetch_categories(lines, cfg_dict, options=args)
    with open(args['dest'], 'w') as f:
        f.writelines(result)
    with open(args['config'], 'w+') as cfg:
        cfg.write(json.dumps(categories,
                  sort_keys=True, indent=4, separators=(',', ': ')))

if __name__ == "__main__":
    sys.exit(main())
