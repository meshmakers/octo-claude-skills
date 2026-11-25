namespace Fixture.Commands.Implementations.Demo;

internal class ImportDemoCommand : JobWithWaitOctoCommand<IDemoClient>
{
    public ImportDemoCommand(ILogger<ImportDemoCommand> logger, IDemoClient client)
        : base(logger, Constants.DemoGroup,
            "ImportDemo",
            "Fixture: a command with arguments and an inherited --wait.")
    {
        _fileArg = CommandArgumentValue.AddArgument("f", "file", ["File to import"], true, 1);
        _replaceArg = CommandArgumentValue.AddArgument("r", "replace", ["Replace existing"], false, 0);
    }
}

internal class ListDemosCommand : Command<OctoToolOptions>
{
    public ListDemosCommand(ILogger<ListDemosCommand> logger) : base(logger, "ListDemos", "Fixture: no group, no arguments.")
    {
    }
}
