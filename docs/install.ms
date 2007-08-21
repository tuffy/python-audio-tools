.\"This work is licensed under the 
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to 
.\"Creative Commons, 
.\"171 Second Street, Suite 300, 
.\"San Francisco, California, 94105, USA.
.SECTION "Installation Procedure"
.PP
To install Python Audio Tools, you simply need to run:
.LP
.ft C
make install
.ft
.LP
as root from the audiotools source directory.
This will use the Python interpreter to install the audiotools
Python module and the executable scripts.
It will then install the man pages from the \fCdoc/\fR
subdirectory.
If you do not have the Construct Python module installed,
you can run:
.LP
.ft C
make construct_install
.ft
.LP
as root from the audiotools source directory to install it.
.PP
To verify your Python Audio Tools installation, run:
.LP
.ft C
audiotools-config
.ft
.LP
as a normal user.
This will load the \fCaudiotools\fR Python module, if possible,
and deliver a listing of available audio formats and current
system settings.

.SUBSECTION "Fixing Installation Problems"
.PP
.RS
.IP \(bu
.B "The audiotools.cdio module doesn't build correctly"
.PP
Check that you have the CDIO library installed, commonly known
as \fClibcdio\fR
.br
If \fClibcdio\fR is installed the module still doesn't build,
ensure that you've also installed any accompanying \fClibcdio-devel\fR
package.
.PP
.IP \(bu
.B "The Construct module isn't found"
.PP
Run the \fCmake construct_install\fR command from the audiotools
source directory, as root, to install this module.
.PP
.IP \(bu
.B "audiotools-config lists formats as unavailable"
.PP
Certain audio formats require external programs.
For instance, to use FLAC files, Python Audio Tools requires the
\fCflac\fR and \fCmetaflac\fR programs.
If these cannot be found in the regular executable
search path or from the config file (which will be explained later),
you will not be able to use that format.
.PP
Check your system's package manager for programs which may be available
but not yet installed.
If that fails to find an appropriate precompiled binary for your system,
use the web sites listed in the `Prerequisites' section
for download and installation instructions.
.PP
.IP \(bu
.B "The system configuration listed by audiotools-config is not correct"
.PP
The FreeDB server, CD-ROM device and file name format are adjustable
from the \fCaudiotools.cfg\fR configuration file, which will be covered
in the next section.
.PP
.IP \(bu
.B "My Python interpreter isn't found, or I wish to use a different one"
.PP
The first line of \fCMakefile\fR is which Python interpreter is being
used for installation of both the Python Audio Tools and Construct module.
For instance, to use a Python interpreter located at
\fC/opt/python/bin/python\fR, you should change that line to read:
.LP
.ft C
export PYTHON = /opt/python/bin/python
.ft
.LP
Running \fCmake\fR will then invoke the new interpreter for
installation of the audiotools module and scripts.
.PP
.RE

.bp

.so configfile.ms
