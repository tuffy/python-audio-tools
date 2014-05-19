/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2014  Brian Langenberger

 This program is free software; you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation; either version 2 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
*******************************************************/

/* config.h.  Generated from config.h.in by configure.  */
/* config.h.in.  Generated from configure.ac by autoheader.  */

/* Have IOKit DVD IOCTL headers */
/* #undef DARWIN_DVD_IOCTL */

/* Define if <extras/BSDI_dvdioctl/dvd.h> defines DVD_STRUCT. */
/* #undef DVD_STRUCT_IN_BSDI_DVDIOCTL_DVD_H */

/* Define if <dvd.h> defines DVD_STRUCT. */
/* #undef DVD_STRUCT_IN_DVD_H */

/* Define if <linux/cdrom.h> defines DVD_STRUCT. */
#define DVD_STRUCT_IN_LINUX_CDROM_H 1

/* Define if <sys/cdio.h> defines dvd_struct. */
/* #undef DVD_STRUCT_IN_SYS_CDIO_H */

/* Define if <sys/dvdio.h> defines dvd_struct. */
/* #undef DVD_STRUCT_IN_SYS_DVDIO_H */

/* Define if FreeBSD-like dvd_struct is defined. */
/* #undef HAVE_BSD_DVD_STRUCT */

/* Define if Linux-like dvd_struct is defined. */
#define HAVE_LINUX_DVD_STRUCT 1

/* Define if OpenBSD-like dvd_struct is defined. */
/* #undef HAVE_OPENBSD_DVD_STRUCT */

/* Define if <sys/scsi.h> defines sctl_io. */
/* #undef HPUX_SCTL_IO */

/* Have userspace SCSI headers. */
/* #undef SOLARIS_USCSI */

/* Have a BeOS system. */
/* #undef SYS_BEOS */

/* Have a Cygwin system. */
/* #undef SYS_CYGWIN */

/* Using Win32. */
/* #undef WIN32 */
