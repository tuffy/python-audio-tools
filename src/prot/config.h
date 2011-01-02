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

/* Define to 1 if you have the <inttypes.h> header file. */
#define HAVE_INTTYPES_H 1

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
