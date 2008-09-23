/*
** Copyright (C) 2001-2008 Erik de Castro Lopo <erikd@mega-nerd.com>
** Portions modified April 2008 by Brian Langenberger
** for use in Python Audio Tools
**
** This program is free software; you can redistribute it and/or modify
** it under the terms of the GNU Lesser General Public License as published by
** the Free Software Foundation; either version 2.1 of the License, or
** (at your option) any later version.
**
** This program is distributed in the hope that it will be useful,
** but WITHOUT ANY WARRANTY; without even the implied warranty of
** MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
** GNU Lesser General Public License for more details.
**
** You should have received a copy of the GNU Lesser General Public License
** along with this program; if not, write to the Free Software
** Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
*/

/* Version 1.4 */

#ifndef FLOAT_CAST_HEADER
#define FLOAT_CAST_HEADER

/*============================================================================
**	On Intel Pentium processors (especially PIII and probably P4), converting
**	from float to int is very slow. To meet the C specs, the code produced by
**	most C compilers targeting Pentium needs to change the FPU rounding mode
**	before the float to int conversion is performed.
**
**	Changing the FPU rounding mode causes the FPU pipeline to be flushed. It
**	is this flushing of the pipeline which is so slow.
**
**	Fortunately the ISO C99 specifications define the functions lrint, lrintf,
**	llrint and llrintf which fix this problem as a side effect.
**
**	On Unix-like systems, the configure process should have detected the
**	presence of these functions. If they weren't found we have to replace them
**	here with a standard C cast.
*/

/*
**	The C99 prototypes for lrint and lrintf are as follows:
**
**		long int lrintf (float x) ;
**		long int lrint  (double x) ;
*/

/*
**	The presence of the required functions are detected during the configure
**	process and the values HAVE_LRINT and HAVE_LRINTF are set accordingly in
**	the config.h file.
*/

#define		HAVE_LRINT_REPLACEMENT	0

/*assuming no LRINT or LRINTF for maximum compatibility*/
#define HAVE_LRINT 0
#define HAVE_LRINTF 0


#include	<math.h>

#define	lrint(dbl)		((long) (dbl))
#define	lrintf(flt)		((long) (flt))

#endif
