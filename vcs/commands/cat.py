from vcs.cli import make_option
from vcs.cli import SingleChangesetCommand


class CatCommand(SingleChangesetCommand):

    option_list = SingleChangesetCommand.option_list + (
        make_option('--blame', action='store_true', dest='blame',
            default=False,
            help='Annotate output with '),
        make_option('--plain', action='store_true', dest='plain',
            default=False,
            help='Simply write output to terminal, don\'t use '
                 'any extra formatting/colors.'),
        make_option('-n', '--line-numbers', action='store_true', dest='linenos',
            default=False, help='Shows line numbers'),
    )

    def get_option_list(self):
        option_list = super(CatCommand, self).get_option_list()
        try:
            __import__('pygments')
            option = make_option('-f', '--formatter', action='store',
                dest='formatter_name', default='terminal',
                help='Pygments specific formatter name.',
            )
            option_list += (option,)
        except ImportError:
            pass
        return option_list

    def get_text(self, node, **options):
        if options.get('plain'):
            return node.content
        formatter_name = options.get('formatter_name')
        if formatter_name:
            from pygments import highlight
            from pygments.formatters import get_formatter_by_name
            formatter = get_formatter_by_name(formatter_name)
            return highlight(node.content, node.lexer, formatter)
        return node.content

    def cat(self, node, **options):
        text = self.get_text(node, **options)

        if options.get('linenos'):
            lines = text.splitlines()
            linenos_width = len(str(len(lines)))
            text = '\n'.join(('{lineno:>{linenos_width}} {line}'.format(
                lineno=lineno + 1, linenos_width=linenos_width,
                line=lines[lineno])
                for lineno in xrange(len(lines))))
            text += '\n'

        if options.get('blame'):
            lines = text.splitlines()
            output = []
            author_width = 15
            for line in xrange(len(lines)):
                cs = node.annotate[line][1]
                output.append('{cid} | {author:<{author_width}} | {line}'.format(
                    cid=cs.raw_id[:6],
                    author=cs.author[:14],
                    author_width=author_width,
                    line=lines[line])
                )
            text = '\n'.join(output)
            text += '\n'

        self.stdout.write(text)


    def handle_arg(self, changeset, arg, **options):
        filename = arg
        node = changeset.get_node(filename)
        self.cat(node, **options)
