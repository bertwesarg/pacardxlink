#!/usr/bin/env python

import os
import sys

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

        self.default_device_menu = gtk.MenuItem('Default device')
        menu.append(self.default_device_menu)
        self.default_device_menu.connect('activate', self.default_device_activate)
        self.default_device_menu.show()
        self.default_device_menu.set_submenu(gtk.Menu())


        self.xlink_devices_menu = gtk.MenuItem('Cross links')
        menu.append(self.xlink_devices_menu)
        self.xlink_devices_menu.connect('activate', self.xlink_devices_activate)
        self.xlink_devices_menu.show()
        self.xlink_devices_menu.set_submenu(gtk.Menu())

        item = gtk.SeparatorMenuItem()
        menu.append(item)
        item.show()

        item = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        menu.append(item)
        item.connect('activate', self.quit_activate)
        item.show()

        self.ai.set_menu(menu)

    def quit_activate(self, w):
        #print 'exit indicator'
        gtk.main_quit()

    def default_device_activate(self, w):
        self.refresh_cards()

        #submenu = gtk.Menu()
        submenu = w.get_submenu()
        for child in submenu.get_children():
            submenu.remove(child)

        # populate devices menu
        for card in self.cards.values():
            #print 'default:', card.index, card.display_name
            self.add_card_to_menu(submenu, card, self.card_set_as_default_activate, card.index)

        w.set_submenu(submenu)

    def xlink_devices_activate(self, w):
        self.refresh_cards()

        #submenu = gtk.Menu()
        submenu = w.get_submenu()
        for child in submenu.get_children():
            submenu.remove(child)

        # populate devices menu
        for card in self.cards.values():
            #print 'xlink:', card.index, card.display_name
            item = self.add_card_to_menu(submenu, card, self.card_xlink_with_activate, card.index)
            item.set_submenu(gtk.Menu())

        if len(self.xlinks):
            item = gtk.SeparatorMenuItem()
            submenu.append(item)
            item.show()

        for xlink in self.xlinks:
            props = self.xlinks[xlink]

            item = gtk.MenuItem(props[2])

            submenu.append(item)
            item.connect('activate', self.xlink_drop_activate, xlink)
            item.show()

        w.set_submenu(submenu)

    def card_xlink_with_activate(self, w, ci):
        self.refresh_cards()
        if ci not in self.cards:
            return
        card = self.cards[ci]

        #submenu = gtk.Menu()
        submenu = w.get_submenu()
        for child in submenu.get_children():
            submenu.remove(child)

        for c in self.cards.values():
            if c.index == card.index:
                continue

            xlink = (card.index, c.index)
            if (c.index, card.index) < xlink:
                xlink = (c.index, card.index)
            if xlink in self.xlinks.keys():
                continue

            #print 'xlink with:', c.index, c.display_name
            self.add_card_to_menu(submenu, c, self.xlink_activate, xlink)

        w.set_submenu(submenu)

    def card_set_as_default_activate(self, w, ci):
        self.refresh_cards()
        if ci not in self.cards:
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

    def xlink_activate(self, w, xlink):
        self.refresh_cards()
        if xlink[0] not in self.cards:
            return
        if xlink[1] not in self.cards:
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
                    'sink=%s' % (card_b_sink.name,),
                    'source_dont_move=on',
                    'sink_dont_move=on'))

        loop_b_a = None
        if card_b_source and card_a_sink:
            loop_b_a = self.pa.module_load('module-loopback',
                    ('latency_msec=1',
                    'source=%s' % (card_b_source.name,),
                    'sink=%s' % (card_a_sink.name,)))

        if (loop_a_b, loop_b_a) == (None, None):
            return

        if loop_a_b is not None and loop_b_a is None:
            name = card_a.display_name + ' > ' + card_b.display_name
        elif loop_a_b is None and loop_b_a is not None:
            name = card_a.display_name + ' < ' + card_b.display_name
        else: #loop_a_b is not None and loop_b_a is not None
            name = card_a.display_name + ' x ' + card_b.display_name

        self.xlinks[xlink] = (loop_a_b, loop_b_a, name)

    def xlink_drop_activate(self, w, xlink):
        self.refresh_cards()
        if xlink not in self.xlinks:
            return
        xlink_props = self.xlinks.pop(xlink)

        if xlink_props[0] is not None:
            self.pa.module_unload(xlink_props[0])
        if xlink_props[1] is not None:
            self.pa.module_unload(xlink_props[1])

    def add_card_to_menu(self, menu, card, action, *args):

        card.icon_name = None
        if 'device.icon_name' in card.proplist.keys():
            card.icon_name = '-'.join(card.proplist['device.icon_name'].split('-')[:-1])

        item = gtk.ImageMenuItem()
        item.set_label(card.display_name)
        if card.icon_name:
            image = gtk.image_new_from_icon_name(card.icon_name, gtk.ICON_SIZE_MENU)
            item.set_image(image)
            item.set_always_show_image(True)

        menu.append(item)
        item.connect('activate', action, *args)
        item.show()

        return item

    def refresh_cards(self):
        self.cards = {}

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

        # drop xlinks, for cards which do not exists anymore
        for xlink in self.xlinks:
            if xlink[0] in self.cards and xlink[1] in self.cards:
                continue

            props = self.xlinks.pop(xlink)
            if xlink_props[0] is not None:
                self.pa.module_unload(props[0])
            if xlink_props[1] is not None:
                self.pa.module_unload(props[1])

if __name__ == '__main__':
    i = PulseCardXLink()

    try:
        gtk.main()
    except:
        pass
