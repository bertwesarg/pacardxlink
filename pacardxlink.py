#!/usr/bin/env python

import os, sys, inspect, traceback

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import appindicator

import pulsectl

class PulseCardXLink(object):

    cards = {}
    xlinks = {}

    def __init__(self):

        self.pa = pulsectl.Pulse('PulseAudio Card XLink')

        self.ai = appindicator.Indicator(
            'pa-card-xlink',
            'audio-headset',
            appindicator.CATEGORY_HARDWARE)
        self.ai.set_status(appindicator.STATUS_ACTIVE)

        # create a menu
        menu = gtk.Menu()

        item = gtk.SeparatorMenuItem()
        menu.append(item)
        item.show()

        item = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        menu.append(item)
        item.connect('activate', self.quit_activate)
        item.show()

        self.static_menu_entries = len(menu.get_children())

        self.ai.set_menu(menu)

        self.refresh_cards()

    def quit_activate(self, w):
        #print 'exit indicator'
        gtk.main_quit()

    def card_activate(self, w, ci):
        if ci not in self.cards.keys():
            return
        card = self.cards[ci]

        # drop all 'other' cards first
        while len(card.menu_sub.get_children()) > 3:
            card.menu_sub.remove(card.menu_sub.get_children()[3])

        for c in self.cards.values():
            if c.index == card.index:
                continue

            xlink = (card.index, c.index)
            if (c.index, card.index) < xlink:
                xlink = (c.index, card.index)
            if xlink in self.xlinks.keys():
                continue

            item = gtk.ImageMenuItem()
            item.set_label(c.display_name)
            if c.icon_name:
                image = gtk.image_new_from_icon_name(c.icon_name, gtk.ICON_SIZE_MENU)
                item.set_image(image)
                item.set_always_show_image(True)

            card.menu_sub.append(item)
            item.connect('activate', self.card_xlink_with_activate, xlink)
            item.show()

        card.menu_item.set_submenu(card.menu_sub)

    def card_set_as_default_activate(self, w, ci):
        if ci not in self.cards.keys():
            return
        card = self.cards[ci]

        for source in self.pa.source_list():
            if source.card == card.index and not source.monitor_of_sink_name:
                self.pa.default_set(source)
                break

        for sink in self.pa.sink_list():
            if sink.card == card.index:
                self.pa.default_set(sink)
                break

    def card_xlink_with_activate(self, w, xlink):
        if xlink[0] not in self.cards.keys():
            return
        if xlink[1] not in self.cards.keys():
            return
        card_a = self.cards[xlink[0]]
        card_b = self.cards[xlink[1]]

        card_a_source = None
        card_b_source = None

        for source in self.pa.source_list():
            if source.card == card_a.index and not card_a_source and not source.monitor_of_sink_name:
                card_a_source = source
            if source.card == card_b.index and not card_b_source and not source.monitor_of_sink_name:
                card_b_source = source

        card_a_sink = None
        card_b_sink = None

        for sink in self.pa.sink_list():
            if sink.card == card_a.index and not card_a_sink:
                card_a_sink = sink
            if sink.card == card_b.index and not card_b_sink:
                card_b_sink = sink

        loop_a_b = None
        if card_a_source and card_b_sink:
            loop_a_b = self.pa.module_load('module-loopback',
                    ('latency_msec=1',
                    'source=%s' % (card_a_source.name,),
                    'sink=%s' % (card_b_sink.name,)))

        loop_b_a = None
        if card_b_source and card_a_sink:
            loop_b_a = self.pa.module_load('module-loopback',
                    ('latency_msec=1',
                    'source=%s' % (card_b_source.name,),
                    'sink=%s' % (card_a_sink.name,)))

        if (loop_a_b, loop_b_a) == (None, None):
            return

        menu = self.ai.get_menu()

        if loop_a_b is not None and loop_b_a is None:
            name = card_a.display_name + ' > ' + card_b.display_name
        elif loop_a_b is None and loop_b_a is not None:
            name = card_a.display_name + ' < ' + card_b.display_name
        else: #loop_a_b is not None and loop_b_a is not None
            name = card_a.display_name + ' x ' + card_b.display_name
        menu_item = gtk.MenuItem(name)

        menu.insert(menu_item, len(menu.get_children()) - self.static_menu_entries)
        menu_item.connect('activate', self.xlink_drop_activate, xlink)
        menu_item.show()

        self.xlinks[xlink] = (loop_a_b, loop_b_a, menu_item)

        self.ai.set_menu(menu)

    def xlink_drop_activate(self, w, xlink):
        if xlink not in self.xlinks.keys():
            return
        xlink_props = self.xlinks.pop(xlink)

        if xlink_props[0] is not None:
            self.pa.module_unload(xlink_props[0])
        if xlink_props[1] is not None:
            self.pa.module_unload(xlink_props[1])
        self.ai.get_menu().remove(xlink_props[2])

    def add_card_to_menu(self, menu, card):

        card.icon_name = None
        if 'device.icon_name' in card.proplist.keys():
            card.icon_name = '-'.join(card.proplist['device.icon_name'].split('-')[:-1])

        card.menu_item = gtk.ImageMenuItem()
        card.menu_item.set_label(card.display_name)
        if card.icon_name:
            image = gtk.image_new_from_icon_name(card.icon_name, gtk.ICON_SIZE_MENU)
            card.menu_item.set_image(image)
            card.menu_item.set_always_show_image(True)

        menu.insert(card.menu_item, len(menu.get_children()) - self.static_menu_entries)
        card.menu_item.connect('activate', self.card_activate, card.index)
        card.menu_item.show()

        card.menu_sub = gtk.Menu()

        item = gtk.MenuItem('Set as default')
        card.menu_sub.append(item)
        #todo disable if this is already the default card?
        item.set_sensitive(True)
        item.connect('activate', self.card_set_as_default_activate, card.index)
        item.show()

        item = gtk.SeparatorMenuItem()
        card.menu_sub.append(item)
        item.show()

        item = gtk.MenuItem('Cross link with:')
        card.menu_sub.append(item)
        item.set_sensitive(False)
        item.show()

        card.menu_item.set_submenu(card.menu_sub)

    def refresh_cards(self):
        # there are not the same, cleanup previous root, if any
        for card in self.cards.values():
            self.ai.get_menu().remove(card.menu_item)
        self.cards = {}
        for xlink in self.xlinks.values():
            self.ai.get_menu().remove(xlink[2])

        for card in self.pa.card_list():
            name = card.name
            if 'device.product.name' in card.proplist.keys():
                name = card.proplist['device.product.name']
            if 'alsa.long_card_name' in card.proplist.keys():
                name = card.proplist['alsa.long_card_name']
            if 'alsa.card_name' in card.proplist.keys():
                name = card.proplist['alsa.card_name']
            card.display_name = name
            self.cards[card.index] = card
            #print card.index, name

        menu = self.ai.get_menu()

        for card in self.cards.values():
            self.add_card_to_menu(menu, card)

        for xlink in self.xlinks.values():
            menu.insert(xlink[2], len(menu.get_children()) - self.static_menu_entries)

        self.ai.set_menu(menu)

if __name__ == '__main__':
    i = PulseCardXLink()

    try:
        gtk.main()
    except:
        pass
