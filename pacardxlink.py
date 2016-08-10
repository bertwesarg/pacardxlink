#!/usr/bin/env python

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import appindicator

import pulsectl

class PulseCardXLink(
    appindicator.Indicator):

    cards = {}
    xlinks = {}

    def __init__(self):

        self.pa = pulsectl.Pulse('PulseAudio Card XLink')

        appindicator.Indicator.__init__(self,
            'pa-card-xlink',
            'audio-headset',
            appindicator.CATEGORY_HARDWARE)
        self.set_status(appindicator.STATUS_ACTIVE)

        # create a menu
        menu = gtk.Menu()

        item = gtk.SeparatorMenuItem()
        menu.append(item)
        item.show()

        item = gtk.MenuItem('Quit')
        menu.append(item)
        item.connect('activate', self.quit_activate)
        item.show()

        self.static_menu_entries = len(menu.get_children())

        self.set_menu(menu)

        self.refresh_cards()

    def quit_activate(self, w):
        #print 'exit indicator'
        gtk.main_quit()

    def card_activate(self, w, ci):
        if ci not in self.cards.keys():
            return
        card = self.cards[ci]

        # drop all 'other' cards first
        while len(card.menu_sub.get_children()) > 2
            card.menu_sub.remove(card.menu_sub.get_children()[2])

        for c in self.cards.values():
            if c.index == card.index:
                continue

            xlink = (card.index, c.index)
            if (c.index, card.index) < xlink:
                xlink = (c.index, card.index)
            if xlink in self.xlinks.keys():
                continue

            item = gtk.MenuItem(c.display_name)
            card.menu_sub.append(item)
            item.connect('activate', self.card_xlink_with_activate, card.index, c.index)
            item.show()

        card.menu_item.set_submenu(card.menu_sub)

        print card.display_name

    def card_set_as_default_activate(self, w, ci):
        if ci not in self.cards.keys():
            return
        card = self.cards[ci]

        print 'set-as-default:', card.display_name

    def add_card_to_menu(self, card):
        menu = self.get_menu()

        card.menu_item = gtk.MenuItem(card.display_name)
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

        self.set_menu(menu)

    def refresh_cards(self):
        # there are not the same, cleanup previous root, if any
        for card in self.cards.values():
            self.get_menu().remove(card.menu_item)
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

        for card in self.cards.values():
            self.add_card_to_menu(card)

if __name__ == '__main__':
    i = PulseCardXLink()

    try:
        gtk.main()
    except:
        pass
